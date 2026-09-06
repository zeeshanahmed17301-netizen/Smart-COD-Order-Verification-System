"""Stream-simulate incoming orders and audit score/factor consistency.

Usage:
    python tmp_score_quality_audit.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.addresses.models import Address
from apps.chatbot.models import ChatbotSettings
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem, OrderSourceSnapshot, RiskFactor
from apps.risk_engine.services import RiskScoringEngine


@dataclass
class CaseResult:
    label: str
    order_id: str
    risk_score: float
    fraud_score: float
    rto_score: float
    address_score: float
    risk_level: str
    action: str
    coverage_score: float
    coverage_label: str
    repeat_phone_3h: int
    repeat_ip_3h: int
    qty_phone_24h: int
    qty_ip_24h: int
    top_factors: list[str]


def ensure_merchant():
    user_model = get_user_model()
    merchant = user_model.objects.order_by("id").first()
    if not merchant:
        merchant = user_model.objects.create_user(
            email="audit-merchant@example.com",
            username="audit_merchant",
            first_name="Audit",
            last_name="Merchant",
            password="StrongPass123!",
        )
    ChatbotSettings.objects.get_or_create(
        merchant=merchant,
        defaults={
            "is_connected": True,
            "language": "urdu",
        },
    )
    return merchant


def build_customer(merchant, phone: str, name: str):
    customer, _ = Customer.objects.get_or_create(
        merchant=merchant,
        phone=phone,
        defaults={
            "name": name,
            "email": f"{phone[-6:]}@example.com",
            "city": "Lahore",
        },
    )
    if not customer.name:
        customer.name = name
    if not customer.city:
        customer.city = "Lahore"
    customer.save(update_fields=["name", "city", "updated_at"])
    return customer


def build_address(customer, *, full_address: str, city: str, district: str, confidence: int, area_rto: int):
    address = Address.objects.create(
        customer=customer,
        full_address=full_address,
        city=city,
        district=district,
        province="Punjab",
        postal_code="54000",
        status="partial" if not district else "valid",
        confidence_score=confidence,
        area_rto_rate=area_rto,
        is_high_risk_area=area_rto >= 35,
    )
    return address


def create_order(
    *,
    merchant,
    customer,
    address,
    label: str,
    amount: Decimal,
    qty: int,
    source_name: str,
    client_ip: str,
    billing_matches_shipping: bool,
    shopify_recommendation: str = "",
    shopify_level: str = "",
    chat_status: str = "unverified",
    include_snapshot: bool = True,
    category: str = "electronics",
):
    order_id = f"AUDIT-{label}-{timezone.now().strftime('%H%M%S%f')}"
    order = Order.objects.create(
        order_id=order_id,
        merchant=merchant,
        customer=customer,
        address=address,
        amount=amount,
        payment_method="cod",
        status="pending",
        source="shopify",
        chat_status=chat_status,
    )

    OrderItem.objects.create(
        order=order,
        name="Audit Product",
        price=(amount / max(qty, 1)).quantize(Decimal("0.01")),
        qty=qty,
        category=category,
    )

    if include_snapshot:
        OrderSourceSnapshot.objects.create(
            order=order,
            source_name=source_name,
            client_ip=client_ip,
            browser_ip=client_ip,
            billing_matches_shipping=billing_matches_shipping,
            shopify_risk_recommendation=shopify_recommendation,
            shopify_risk_level=shopify_level,
        )

    result = RiskScoringEngine.score_and_save(order)
    order.refresh_from_db()
    enrichment = order.enrichment
    factors = list(
        RiskFactor.objects.filter(order=order)
        .order_by("-score")
        .values_list("name", flat=True)[:6]
    )
    info_quality = result.information_quality or {}

    return CaseResult(
        label=label,
        order_id=order.order_id,
        risk_score=float(result.risk_score),
        fraud_score=float(result.fraud_score),
        rto_score=float(result.rto_probability_score),
        address_score=float(result.address_score),
        risk_level=result.risk_level,
        action=result.recommended_action,
        coverage_score=float(info_quality.get("coverage_score", 0.0)),
        coverage_label=str(info_quality.get("coverage_label", "")),
        repeat_phone_3h=int(enrichment.repeat_phone_orders_3h),
        repeat_ip_3h=int(enrichment.repeat_ip_orders_3h),
        qty_phone_24h=int(enrichment.total_qty_same_phone_24h),
        qty_ip_24h=int(enrichment.total_qty_same_ip_24h),
        top_factors=factors,
    )


def print_case(case: CaseResult):
    print("-" * 110)
    print(f"{case.label} | {case.order_id}")
    print(
        f"score: risk={case.risk_score:.1f}, fraud={case.fraud_score:.1f}, "
        f"rto={case.rto_score:.1f}, address={case.address_score:.1f}"
    )
    print(
        f"decision: level={case.risk_level}, action={case.action}, "
        f"quality={case.coverage_label} ({case.coverage_score:.1f})"
    )
    print(
        f"velocity: repeat_phone_3h={case.repeat_phone_3h}, repeat_ip_3h={case.repeat_ip_3h}, "
        f"qty_phone_24h={case.qty_phone_24h}, qty_ip_24h={case.qty_ip_24h}"
    )
    print(f"top_factors: {case.top_factors}")


def detect_findings(cases: list[CaseResult]):
    findings: list[str] = []

    for case in cases:
        if not (0.0 <= case.risk_score <= 100.0):
            findings.append(f"{case.label}: risk_score out of bounds ({case.risk_score})")
        if not (0.0 <= case.fraud_score <= 100.0):
            findings.append(f"{case.label}: fraud_score out of bounds ({case.fraud_score})")
        if not (0.0 <= case.rto_score <= 100.0):
            findings.append(f"{case.label}: rto_score out of bounds ({case.rto_score})")

    for current, previous in zip(cases[1:], cases[:-1]):
        jump = current.fraud_score - previous.fraud_score
        if jump >= 45.0 and current.repeat_phone_3h >= 3:
            findings.append(
                f"{current.label}: very steep fraud jump (+{jump:.1f}) once repeat_phone_3h reached {current.repeat_phone_3h}."
            )
        if jump >= 45.0 and current.qty_phone_24h >= 3:
            findings.append(
                f"{current.label}: very steep fraud jump (+{jump:.1f}) once qty_phone_24h reached {current.qty_phone_24h}."
            )

    for case in cases:
        if case.action == "ship_order" and case.risk_level in {"high", "critical"}:
            findings.append(
                f"{case.label}: action/level mismatch (ship_order with {case.risk_level})."
            )

    for case in cases:
        if case.action == "cancel_order" and case.risk_score < 40.0:
            findings.append(
                f"{case.label}: cancel_order fired while composite risk_score stayed low ({case.risk_score:.1f})."
            )

    for case in cases:
        if case.action == "ship_order" and case.coverage_label in {"partial", "weak"}:
            findings.append(
                f"{case.label}: ship_order returned even with {case.coverage_label} evidence coverage."
            )

    return findings


def run():
    merchant = ensure_merchant()
    run_suffix = timezone.now().strftime("%H%M%S")
    stream_ip = f"198.18.{int(run_suffix[-2:]) % 250}.{int(run_suffix[-1:]) + 10}"
    stream_source = f"audit_stream_{run_suffix}"
    risky_ip = f"198.51.{int(run_suffix[-2:]) % 250}.{int(run_suffix[-1:]) + 40}"

    def mk_phone(seed: str) -> str:
        # Always produce a local-format PK number: 03 + 9 digits
        return f"03{run_suffix[-4:]}{seed:0>5}"[:11]

    # Stream A: low -> medium -> high velocity on same identity/IP
    stream_customer = build_customer(merchant, phone=mk_phone("1"), name="Audit Stream")
    stream_address = build_address(
        stream_customer,
        full_address="Street 10, Johar Town, Lahore",
        city="Lahore",
        district="Johar Town",
        confidence=82,
        area_rto=12,
    )

    stream_cases: list[CaseResult] = []
    for idx, amount in enumerate((Decimal("1800.00"), Decimal("1800.00"), Decimal("1800.00"), Decimal("1800.00")), start=1):
        stream_cases.append(
            create_order(
                merchant=merchant,
                customer=stream_customer,
                address=stream_address,
                label=f"STREAM-{idx}",
                amount=amount,
                qty=1,
                source_name=stream_source,
                client_ip=stream_ip,
                billing_matches_shipping=True,
                shopify_recommendation="",
                shopify_level="",
                chat_status="unverified",
                category=f"auditcat_{run_suffix}",
            )
        )

    # Stream B: address weakness + shopify investigate
    risky_customer = build_customer(merchant, phone=mk_phone("2"), name="Audit Risky")
    weak_address = build_address(
        risky_customer,
        full_address="Near Main Stop",
        city="Peshawar",
        district="",
        confidence=35,
        area_rto=42,
    )

    stream_cases.append(
        create_order(
            merchant=merchant,
            customer=risky_customer,
            address=weak_address,
            label="RISKY-INVESTIGATE",
            amount=Decimal("14500.00"),
            qty=2,
            source_name="facebook_ad",
            client_ip=risky_ip,
            billing_matches_shipping=False,
            shopify_recommendation="INVESTIGATE",
            shopify_level="HIGH",
            chat_status="no_response",
        )
    )

    # Stream C: no source snapshot / sparse evidence
    sparse_customer = build_customer(merchant, phone=mk_phone("3"), name="Audit Sparse")
    sparse_address = build_address(
        sparse_customer,
        full_address="Street 1",
        city="Lahore",
        district="",
        confidence=45,
        area_rto=20,
    )
    stream_cases.append(
        create_order(
            merchant=merchant,
            customer=sparse_customer,
            address=sparse_address,
            label="SPARSE-NO-SNAPSHOT",
            amount=Decimal("1200.00"),
            qty=1,
            source_name="",
            client_ip="",
            billing_matches_shipping=True,
            shopify_recommendation="",
            shopify_level="",
            chat_status="unverified",
            include_snapshot=False,
        )
    )

    for case in stream_cases:
        print_case(case)

    findings = detect_findings(stream_cases)
    print("=" * 110)
    if findings:
        print("FINDINGS")
        for idx, finding in enumerate(findings, start=1):
            print(f"{idx}. {finding}")
    else:
        print("No hard inconsistencies detected from this simulation pass.")


if __name__ == "__main__":
    run()

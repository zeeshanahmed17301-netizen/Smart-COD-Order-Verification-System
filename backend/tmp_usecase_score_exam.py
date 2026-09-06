"""Examine score use-cases across many simulated incoming orders.

Outputs a matrix focused on:
Courier | Overall Risk | Address Score | Fraud Prob. | RTO Prob. | WhatsApp Status | Action
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from decimal import Decimal

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.addresses.models import Address
from apps.chatbot.models import ChatbotSettings
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem, OrderSourceSnapshot
from apps.risk_engine.services import RiskScoringEngine, ScoreCalibrationService


@dataclass
class CaseRow:
    order_id: str
    courier: str
    overall_risk: str
    risk_score: float
    address_score: float
    fraud_prob: float
    fraud_score: float
    rto_prob: float
    rto_score: float
    whatsapp_status: str
    action: str


def ensure_isolated_merchant(tag: str):
    user_model = get_user_model()
    merchant = user_model.objects.create_user(
        email=f"score-matrix-{tag}@example.com",
        username=f"score_matrix_{tag}",
        first_name="Score",
        last_name="Matrix",
        password="StrongPass123!",
    )
    ChatbotSettings.objects.create(
        merchant=merchant,
        is_connected=True,
        language="urdu",
    )
    return merchant


def courier_bucket(reachable: bool | None, coverage: float, confidence: str) -> str:
    if reachable is False:
        return "unreachable"
    if reachable is True and coverage >= 66:
        return "strong"
    if reachable is True and coverage > 0:
        return "limited"
    if confidence and confidence != "none":
        return "partial"
    return "unknown"


def addr_band(score: float) -> str:
    if score >= 85:
        return "strong"
    if score >= 65:
        return "usable"
    if score >= 45:
        return "weak"
    return "poor"


def prob_band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "very_low"


def build_or_get_customer(merchant, phone: str, city: str, with_email: bool):
    customer, _ = Customer.objects.get_or_create(
        merchant=merchant,
        phone=phone,
        defaults={
            "name": f"Sim {phone[-4:]}",
            "email": f"sim{phone[-4:]}@example.com" if with_email else "",
            "city": city,
        },
    )
    if with_email and not customer.email:
        customer.email = f"sim{phone[-4:]}@example.com"
    if not with_email:
        customer.email = ""
    customer.city = city
    customer.name = customer.name or f"Sim {phone[-4:]}"
    customer.save(update_fields=["email", "city", "name", "updated_at"])
    return customer


def maybe_record_outcome(order, p: float = 0.38):
    if random.random() > p:
        return
    if order.status in {"delivered", "rto", "cancelled"}:
        return

    outcomes = ["delivered", "rto", "refused", "wrong_address"]
    weights = [0.58, 0.25, 0.10, 0.07]
    outcome_value = random.choices(outcomes, weights=weights, k=1)[0]
    normalized_status = "delivered" if outcome_value == "delivered" else "rto"

    order.status = normalized_status
    order.save(update_fields=["status", "updated_at"])

    customer = order.customer
    if normalized_status == "delivered":
        customer.delivered_count += 1
    else:
        customer.rto_count += 1
    customer.save(update_fields=["delivered_count", "rto_count", "updated_at"])


def run(total_orders: int = 120):
    tag = timezone.now().strftime("%H%M%S")
    random.seed(int(tag))

    merchant = ensure_isolated_merchant(tag)

    cities = ["Lahore", "Karachi", "Islamabad", "Peshawar", f"NoCity{tag}"]
    statuses = ["confirmed", "unverified", "no_response", "timeout"]
    sources = ["facebook_ad", "google", "unknown", "tiktok", f"matrix_src_{tag}"]
    categories = ["electronics", "home", "beauty", "fashion", f"matrix_cat_{tag}"]

    phone_pool = [f"03{tag[-4:]}{i:05d}"[:11] for i in range(1, 11)]
    ip_pool = [f"198.19.{int(tag[-2:]) % 250}.{i}" for i in range(10, 30)]

    rows: list[CaseRow] = []

    with patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", return_value="MOCK_SID"):
        for idx in range(total_orders):
            city = random.choice(cities)
            chat_status = random.choice(statuses)
            source_name = random.choice(sources)
            category = random.choice(categories)
            phone = random.choice(phone_pool)
            ip = random.choice(ip_pool)
            with_email = random.random() > 0.25
            billing_matches = random.random() > 0.35

            rec = random.choices(["", "INVESTIGATE", "CANCEL"], weights=[0.78, 0.18, 0.04], k=1)[0]
            level = ""
            if rec == "INVESTIGATE":
                level = random.choice(["MEDIUM", "HIGH"])
            elif rec == "CANCEL":
                level = "HIGH"

            customer = build_or_get_customer(merchant, phone=phone, city=city, with_email=with_email)

            area_rto = random.randint(4, 45) if city.startswith("NoCity") else random.randint(2, 35)
            confidence = random.randint(30, 92)
            district = "" if random.random() > 0.45 else "Model Town"

            address = Address.objects.create(
                customer=customer,
                full_address=("Near Stop" if random.random() > 0.55 else "House 12, Street 5"),
                city=city,
                district=district,
                province="Punjab",
                postal_code="54000" if random.random() > 0.35 else "",
                status="partial" if not district else "valid",
                confidence_score=confidence,
                area_rto_rate=area_rto,
                is_high_risk_area=area_rto >= 35,
            )

            amount = Decimal(str(random.choice([1200, 1800, 2400, 5200, 9800, 14500])))
            qty = random.choice([1, 1, 1, 2, 3])

            order = Order.objects.create(
                order_id=f"MATRIX-{idx+1}-{timezone.now().strftime('%H%M%S%f')}",
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
                name="Sim Product",
                price=(amount / max(qty, 1)).quantize(Decimal("0.01")),
                qty=qty,
                category=category,
            )

            include_snapshot = random.random() > 0.12
            if include_snapshot:
                OrderSourceSnapshot.objects.create(
                    order=order,
                    source_name=source_name,
                    client_ip=ip,
                    browser_ip=ip,
                    billing_matches_shipping=billing_matches,
                    shopify_risk_recommendation=rec,
                    shopify_risk_level=level,
                )

            result = RiskScoringEngine.score_and_save(order)
            order.refresh_from_db()
            maybe_record_outcome(order)

            enrichment = order.enrichment
            fraud_probability = ScoreCalibrationService.calibrate(
                target="fraud",
                score=result.fraud_score,
                version=result.calibration_version,
            ).probability
            rto_probability = ScoreCalibrationService.calibrate(
                target="rto",
                score=result.rto_probability_score,
                version=result.calibration_version,
            ).probability

            row = CaseRow(
                order_id=order.order_id,
                courier=courier_bucket(
                    reachable=enrichment.courier_reachable,
                    coverage=float(enrichment.courier_coverage_score or 0.0),
                    confidence=str(enrichment.courier_match_confidence or ""),
                ),
                overall_risk=result.risk_level,
                risk_score=float(result.risk_score),
                address_score=float(result.address_score),
                fraud_prob=float(fraud_probability),
                fraud_score=float(result.fraud_score),
                rto_prob=float(rto_probability),
                rto_score=float(result.rto_probability_score),
                whatsapp_status=order.chat_status,
                action=result.recommended_action,
            )
            rows.append(row)

    # ---- Matrix and diagnostics ----
    print("=" * 120)
    print(f"SIMULATED ORDERS: {len(rows)}")

    action_counts: dict[str, int] = {}
    for row in rows:
        action_counts[row.action] = action_counts.get(row.action, 0) + 1

    print("\nAction distribution:")
    for action, count in sorted(action_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {action}: {count}")

    matrix_counts: dict[tuple, int] = {}
    for row in rows:
        key = (
            row.courier,
            row.overall_risk,
            addr_band(row.address_score),
            prob_band(row.fraud_score),
            prob_band(row.rto_score),
            row.whatsapp_status,
            row.action,
        )
        matrix_counts[key] = matrix_counts.get(key, 0) + 1

    print("\nTop use-cases (Courier | Overall Risk | Address Score | Fraud Prob. | RTO Prob. | WhatsApp Status | Action):")
    for key, count in sorted(matrix_counts.items(), key=lambda x: (-x[1], x[0]))[:30]:
        print(f"- {key[0]} | {key[1]} | {key[2]} | {key[3]} | {key[4]} | {key[5]} | {key[6]} => {count}")

    anomalies = []
    for row in rows:
        if row.action == "cancel_order" and row.risk_score < 40:
            anomalies.append(f"{row.order_id}: cancel_order with low composite risk_score={row.risk_score:.1f}")
        if row.action == "ship_order" and row.fraud_score >= 70:
            anomalies.append(f"{row.order_id}: ship_order with high fraud_score={row.fraud_score:.1f}")
        if row.action == "ship_order" and row.rto_score >= 70:
            anomalies.append(f"{row.order_id}: ship_order with high rto_score={row.rto_score:.1f}")

    print("\nAnomaly checks:")
    if not anomalies:
        print("- No hard contradictions in action vs score thresholds were detected in this run.")
    else:
        print(f"- Found {len(anomalies)} potential contradictions.")
        for line in anomalies[:20]:
            print(f"  * {line}")

    # Branch reachability insight
    print("\nDecision-branch coverage insight:")
    expected_actions = ["ship_order", "verify_address", "call_customer", "manual_review", "cancel_order"]
    for action in expected_actions:
        print(f"- {action}: {action_counts.get(action, 0)}")


if __name__ == "__main__":
    run()

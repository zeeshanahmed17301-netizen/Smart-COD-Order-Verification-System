"""Manual Pakistan-focused flow data test for order risk pipelines.

Usage:
    python test_flow_data_pipeline.py
"""

from __future__ import annotations

import os
from decimal import Decimal

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.addresses.models import Address
from apps.chatbot.models import ChatbotSettings, Conversation
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem, OrderSourceSnapshot, RiskFactor
from apps.risk_engine.services import RiskScoringEngine


def _get_merchant():
    user_model = get_user_model()
    merchant = (
        user_model.objects.filter(chatbot_settings__is_connected=True)
        .order_by("id")
        .first()
    )
    if merchant:
        return merchant

    merchant = user_model.objects.order_by("id").first()
    if not merchant:
        raise RuntimeError("No merchant user found. Create a user first.")

    ChatbotSettings.objects.get_or_create(
        merchant=merchant,
        defaults={
            "is_connected": True,
            "language": "urdu",
            "whatsapp_number": "+923001234567",
        },
    )
    return merchant


def _seed_history_for_customer(merchant, customer, prefix: str) -> None:
    """Create resolved historical outcomes to shape customer/source risk."""
    base_address, _ = Address.objects.get_or_create(
        customer=customer,
        full_address="Street 10, Gulberg, Lahore",
        defaults={
            "city": "Lahore",
            "district": "Gulberg",
            "province": "Punjab",
            "postal_code": "54000",
            "status": "valid",
            "confidence_score": 88,
            "area_rto_rate": 8,
        },
    )

    historical_data = [
        ("delivered", "shopify", "facebook_ad"),
        ("rto", "shopify", "facebook_ad"),
        ("rto", "shopify", "facebook_ad"),
    ]

    for idx, (status_value, source, source_name) in enumerate(historical_data, start=1):
        order = Order.objects.create(
            order_id=f"{prefix}-HIST-{idx}-{timezone.now().strftime('%H%M%S%f')}",
            merchant=merchant,
            customer=customer,
            address=base_address,
            amount=Decimal("2200.00"),
            payment_method="cod",
            status=status_value,
            source=source,
            chat_status="confirmed" if status_value == "delivered" else "no_response",
        )
        OrderItem.objects.create(
            order=order,
            name="History Item",
            price=Decimal("2200.00"),
            qty=1,
            category="electronics",
        )
        OrderSourceSnapshot.objects.create(
            order=order,
            source_name=source_name,
            client_ip=f"39.37.10.{idx}",
            browser_ip=f"39.37.10.{idx}",
            billing_matches_shipping=True,
        )
        customer.total_orders += 1
        if status_value == "delivered":
            customer.delivered_count += 1
        elif status_value == "rto":
            customer.rto_count += 1

    customer.save(update_fields=["total_orders", "delivered_count", "rto_count", "updated_at"])


def _create_flow_orders(merchant):
    # Low-risk profile (Islamabad)
    c1 = Customer.objects.create(
        merchant=merchant,
        name="Ali Raza",
        phone="+923001112223",
        email="ali.raza@example.com",
        city="Islamabad",
    )
    a1 = Address.objects.create(
        customer=c1,
        full_address="House 22, Street 5, G-11, Islamabad",
        city="Islamabad",
        district="G-11",
        province="Islamabad Capital Territory",
        postal_code="44000",
        status="valid",
        confidence_score=92,
        area_rto_rate=6,
    )

    # Medium-risk profile (Karachi, partial address)
    c2 = Customer.objects.create(
        merchant=merchant,
        name="Sadia Khan",
        phone="+923114445556",
        email="",
        city="Karachi",
    )
    a2 = Address.objects.create(
        customer=c2,
        full_address="Street 9, Karachi",
        city="Karachi",
        district="",
        province="Sindh",
        postal_code="",
        status="partial",
        confidence_score=58,
        area_rto_rate=28,
    )

    # High-risk profile (Peshawar, repeated IP, Shopify investigate)
    c3 = Customer.objects.create(
        merchant=merchant,
        name="Imran Shah",
        phone="+923209998887",
        email="imran.shah@example.com",
        city="Peshawar",
    )
    _seed_history_for_customer(merchant, c3, prefix="PKFLOW")
    a3 = Address.objects.create(
        customer=c3,
        full_address="Near Ring Road, Peshawar",
        city="Peshawar",
        district="",
        province="KPK",
        postal_code="25000",
        status="partial",
        confidence_score=42,
        area_rto_rate=36,
        is_high_risk_area=True,
    )

    payload = [
        {
            "label": "LOW",
            "order_id": f"PKFLOW-LOW-{timezone.now().strftime('%H%M%S%f')}",
            "customer": c1,
            "address": a1,
            "amount": Decimal("1890.00"),
            "source": "shopify",
            "chat_status": "confirmed",
            "source_snapshot": {
                "source_name": "google",
                "client_ip": "39.39.11.11",
                "browser_ip": "39.39.11.11",
                "billing_matches_shipping": True,
                "shopify_risk_recommendation": "",
                "shopify_risk_level": "",
            },
            "items": [
                ("Phone Cover", Decimal("890.00"), 1, "accessories"),
                ("USB Cable", Decimal("1000.00"), 1, "electronics"),
            ],
        },
        {
            "label": "MEDIUM",
            "order_id": f"PKFLOW-MED-{timezone.now().strftime('%H%M%S%f')}",
            "customer": c2,
            "address": a2,
            "amount": Decimal("5400.00"),
            "source": "shopify",
            "chat_status": "unverified",
            "source_snapshot": {
                "source_name": "facebook_ad",
                "client_ip": "103.120.66.44",
                "browser_ip": "103.120.66.44",
                "billing_matches_shipping": False,
                "shopify_risk_recommendation": "INVESTIGATE",
                "shopify_risk_level": "MEDIUM",
            },
            "items": [
                ("Blender", Decimal("2700.00"), 2, "home"),
            ],
        },
        {
            "label": "HIGH",
            "order_id": f"PKFLOW-HIGH-{timezone.now().strftime('%H%M%S%f')}",
            "customer": c3,
            "address": a3,
            "amount": Decimal("15990.00"),
            "source": "shopify",
            "chat_status": "no_response",
            "source_snapshot": {
                "source_name": "facebook_ad",
                "client_ip": "203.0.113.44",
                "browser_ip": "203.0.113.44",
                "billing_matches_shipping": False,
                "shopify_risk_recommendation": "INVESTIGATE",
                "shopify_risk_level": "HIGH",
            },
            "items": [
                ("Drone Camera", Decimal("5330.00"), 3, "electronics"),
            ],
        },
    ]

    created = []
    for row in payload:
        order = Order.objects.create(
            order_id=row["order_id"],
            merchant=merchant,
            customer=row["customer"],
            address=row["address"],
            amount=row["amount"],
            payment_method="cod",
            status="pending",
            source=row["source"],
            chat_status=row["chat_status"],
        )
        for item_name, price, qty, category in row["items"]:
            OrderItem.objects.create(
                order=order,
                name=item_name,
                price=price,
                qty=qty,
                category=category,
            )
        OrderSourceSnapshot.objects.create(order=order, **row["source_snapshot"])
        created.append((row["label"], order))

    return created


def _print_order_result(label: str, order: Order) -> None:
    order.refresh_from_db()
    enrichment = order.enrichment
    conversation = Conversation.objects.filter(order=order).first()
    top_factors = list(
        RiskFactor.objects.filter(order=order)
        .order_by("-score")
        .values_list("name", "score")[:4]
    )

    print("-" * 90)
    print(f"{label} | {order.order_id} | city={order.address.city} | district={order.address.district or '-'}")
    print(
        "scores: "
        f"risk={order.risk_score:.1f}, fraud={order.fraud_score:.1f}, "
        f"rto={order.rto_probability_score:.1f}, address={order.address_score:.1f}"
    )
    print(
        "decision: "
        f"level={order.risk_level}, action={order.recommended_action}, chat={order.chat_status}"
    )
    print(
        "enrichment: "
        f"status={enrichment.enrichment_status}, provider={enrichment.address_provider}, "
        f"contactability={enrichment.contactability_score:.1f}, ip_risk={enrichment.ip_risk_score:.1f}"
    )
    print(
        "velocity: "
        f"repeat_ip_7d={enrichment.repeat_ip_orders_7d}, repeat_phone_30d={enrichment.repeat_phone_orders_30d}, "
        f"qty_phone_24h={enrichment.total_qty_same_phone_24h}, qty_ip_24h={enrichment.total_qty_same_ip_24h}"
    )
    print(f"conversation: {conversation.status if conversation else 'none'}")
    print(f"top factors: {top_factors}")


def run() -> int:
    merchant = _get_merchant()
    print(f"Merchant for flow test: {merchant.email} (id={merchant.id})")

    created_orders = _create_flow_orders(merchant)

    print("\nRunning scoring pipeline per order...")
    for label, order in created_orders:
        result = RiskScoringEngine.score_and_save(order)
        print(
            f"pipeline result ({label}): "
            f"risk_level={result.risk_level}, action={result.recommended_action}, "
            f"fraud={result.fraud_score:.1f}, rto={result.rto_probability_score:.1f}"
        )

    print("\nRunning backfill pipeline for created merchant...")
    call_command("backfill_risk_scores", merchant_email=merchant.email, limit=25)

    print("\nFinal order snapshots:")
    for label, order in created_orders:
        _print_order_result(label, order)

    print("\nPakistan flow data test finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

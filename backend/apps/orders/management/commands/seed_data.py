"""
Management command to seed realistic demo data matching frontend mockData.js.
Usage: python manage.py seed_data
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import MerchantProfile
from apps.customers.models import Customer
from apps.addresses.models import Address
from apps.orders.models import Order, OrderItem, RiskFactor
from apps.chatbot.models import (
    ChatbotSettings, Conversation, Message, WhatsAppInteraction,
)
from apps.stores.models import StoreConnection, APIKey, Webhook

User = get_user_model()

# ── Seed data matching mockData.js ──────────────────────────────────────────
CUSTOMERS = [
    {"name": "Ali Khan", "phone": "+92 300 1234567", "email": "ali.khan@example.com", "city": "Karachi"},
    {"name": "Sara Ahmed", "phone": "+92 321 9876543", "email": "sara.ahmed@example.com", "city": "Lahore"},
    {"name": "Bilal T.", "phone": "+92 333 5555555", "email": "bilal.t@example.com", "city": "Islamabad"},
    {"name": "Zainab B.", "phone": "+92 345 1112223", "email": "zainab.b@example.com", "city": "Faisalabad"},
    {"name": "Usman G.", "phone": "+92 312 4443332", "email": "usman.g@example.com", "city": "Multan"},
    {"name": "Fatima R.", "phone": "+92 301 7778889", "email": "fatima.r@example.com", "city": "Rawalpindi"},
    {"name": "Hassan M.", "phone": "+92 315 2223334", "email": "hassan.m@example.com", "city": "Peshawar"},
    {"name": "Ayesha S.", "phone": "+92 322 6667778", "email": "ayesha.s@example.com", "city": "Quetta"},
    {"name": "Omar F.", "phone": "+92 334 8889990", "email": "omar.f@example.com", "city": "Hyderabad"},
    {"name": "Mariam K.", "phone": "+92 313 4445556", "email": "mariam.k@example.com", "city": "Sialkot"},
]

ORDERS_DATA = [
    {
        "order_id": "ORD-001", "customer_idx": 0, "amount": 4500,
        "status": "pending", "risk_score": 85, "risk_level": "high",
        "fraud_score": 15, "address_score": 85, "rto_probability": "Low",
        "chat_status": "unverified", "recommended_action": "verify_address",
        "items": [
            {"name": "Wireless Earbuds", "price": 2000, "qty": 1},
            {"name": "Smart Watch", "price": 2500, "qty": 1},
        ],
        "risk_factors": [
            {"name": "High RTO History", "score": 90, "level": "critical"},
            {"name": "Address Mismatch", "score": 60, "level": "medium"},
            {"name": "High Value Order", "score": 40, "level": "low"},
        ],
    },
    {
        "order_id": "ORD-002", "customer_idx": 1, "amount": 1200,
        "status": "verified", "risk_score": 15, "risk_level": "low",
        "fraud_score": 5, "address_score": 98, "rto_probability": "Very Low",
        "chat_status": "confirmed", "recommended_action": "ship_order",
        "items": [{"name": "Cotton T-Shirt", "price": 1200, "qty": 1}],
        "risk_factors": [],
    },
    {
        "order_id": "ORD-003", "customer_idx": 2, "amount": 8900,
        "status": "rejected", "risk_score": 92, "risk_level": "critical",
        "fraud_score": 88, "address_score": 45, "rto_probability": "High",
        "chat_status": "denied", "recommended_action": "cancel_order",
        "items": [
            {"name": "Gaming Keyboard", "price": 6500, "qty": 1},
            {"name": "Mouse", "price": 2400, "qty": 1},
        ],
        "risk_factors": [
            {"name": "Blacklisted Customer", "score": 100, "level": "critical"},
            {"name": "High Value Order", "score": 70, "level": "high"},
            {"name": "Address Mismatch", "score": 55, "level": "medium"},
        ],
    },
    {
        "order_id": "ORD-004", "customer_idx": 3, "amount": 3200,
        "status": "pending", "risk_score": 45, "risk_level": "medium",
        "fraud_score": 45, "address_score": 60, "rto_probability": "Medium",
        "chat_status": "no_response", "recommended_action": "call_customer",
        "items": [{"name": "Makeup Kit", "price": 3200, "qty": 1}],
        "risk_factors": [
            {"name": "No Response to Chat", "score": 50, "level": "medium"},
            {"name": "Moderate Address Risk", "score": 40, "level": "medium"},
        ],
    },
    {
        "order_id": "ORD-005", "customer_idx": 4, "amount": 15000,
        "status": "verified", "risk_score": 10, "risk_level": "low",
        "fraud_score": 8, "address_score": 92, "rto_probability": "Low",
        "chat_status": "confirmed", "recommended_action": "ship_order",
        "items": [{"name": "Smartphone", "price": 15000, "qty": 1}],
        "risk_factors": [],
    },
]

ADDRESSES = [
    {"full": "House 123, Street 4, Block 5, Gulshan-e-Iqbal, Karachi", "suggested": "House 123, Street 4, Block 5, Gulshan-e-Iqbal, Karachi City, Sindh, Pakistan", "confidence": 95, "status": "valid"},
    {"full": "Flat 7, Model Town, Lahore", "suggested": "Flat 7, Model Town, Lahore, Punjab, Pakistan", "confidence": 98, "status": "valid"},
    {"full": "G-11/2, Islamabad", "suggested": "G-11/2, Islamabad Capital Territory, Pakistan", "confidence": 45, "status": "mismatch"},
    {"full": "Sadar Road, Faisalabad", "suggested": "Sadar Road, Faisalabad, Punjab, Pakistan", "confidence": 60, "status": "partial"},
    {"full": "Bosan Road, Multan", "suggested": "Bosan Road, Multan, Punjab, Pakistan", "confidence": 92, "status": "valid"},
    {"full": "Committee Chowk, Rawalpindi", "suggested": "Committee Chowk, Rawalpindi, Punjab, Pakistan", "confidence": 88, "status": "valid"},
    {"full": "University Road, Peshawar", "suggested": "University Road, Peshawar, KPK, Pakistan", "confidence": 70, "status": "partial"},
    {"full": "Jinnah Town, Quetta", "suggested": "Jinnah Town, Quetta, Balochistan, Pakistan", "confidence": 55, "status": "partial"},
    {"full": "Latifabad, Hyderabad", "suggested": "Latifabad, Hyderabad, Sindh, Pakistan", "confidence": 80, "status": "valid"},
    {"full": "Cantt Area, Sialkot", "suggested": "Cantt Area, Sialkot, Punjab, Pakistan", "confidence": 90, "status": "valid"},
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo data matching frontend mockData.js"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding Risk-Guard demo data...")

        # ── Create demo merchant ────────────────────────────────────────
        user, created = User.objects.get_or_create(
            email="demo@riskguard.pk",
            defaults={
                "username": "demo_merchant",
                "first_name": "Demo",
                "last_name": "Merchant",
                "is_onboarded": True,
            },
        )
        if created:
            user.set_password("RiskGuard@2024")
            user.save()
            self.stdout.write(self.style.SUCCESS("  ✓ Demo user created (demo@riskguard.pk / RiskGuard@2024)"))

        # ── Merchant profile ────────────────────────────────────────────
        profile, _ = MerchantProfile.objects.get_or_create(
            user=user,
            defaults={
                "store_name": "Demo Electronics Store",
                "category": "electronics",
                "country": "Pakistan",
                "whatsapp_number": "+92 300 1234567",
                "language": "urdu",
                "auto_send": "immediately",
                "auto_cancel": "1hour",
            },
        )
        self.stdout.write("  ✓ Merchant profile ready")

        # ── Chatbot settings ────────────────────────────────────────────
        ChatbotSettings.objects.get_or_create(
            merchant=user,
            defaults={
                "whatsapp_number": "+92 300 1234567",
                "is_connected": True,
                "language": "urdu",
            },
        )
        self.stdout.write("  ✓ Chatbot settings created")

        # ── Store connections ───────────────────────────────────────────
        StoreConnection.objects.get_or_create(
            merchant=user,
            platform="shopify",
            defaults={
                "store_url": "https://demo-store.riskguard.pk",
                "is_active": True,
                "last_sync_at": timezone.now(),
            },
        )
        self.stdout.write("  ✓ Store connection created")

        # ── API keys ───────────────────────────────────────────────────
        if not APIKey.objects.filter(merchant=user).exists():
            APIKey.objects.create(
                merchant=user,
                key="rg_live_k3y_7x9p2mNq4wRt6vBc",
                secret="rg_secret_Hn8kL2pQ5xYz9wVm",
                label="Default",
            )
        self.stdout.write("  ✓ API keys created")

        # ── Webhooks ───────────────────────────────────────────────────
        Webhook.objects.get_or_create(
            merchant=user,
            event="order.verified",
            defaults={
                "url": "https://yourstore.com/webhooks/riskguard",
                "is_active": True,
                "delivery_count": 1234,
            },
        )
        Webhook.objects.get_or_create(
            merchant=user,
            event="order.rejected",
            defaults={
                "url": "https://yourstore.com/webhooks/rejected",
                "is_active": True,
                "delivery_count": 15,
            },
        )
        self.stdout.write("  ✓ Webhooks created")

        # ── Customers ──────────────────────────────────────────────────
        customer_objs = []
        for i, c_data in enumerate(CUSTOMERS):
            customer, _ = Customer.objects.get_or_create(
                merchant=user,
                phone=c_data["phone"],
                defaults={
                    "name": c_data["name"],
                    "email": c_data["email"],
                    "city": c_data["city"],
                    "total_orders": random.randint(1, 15),
                    "delivered_count": random.randint(0, 8),
                    "rto_count": random.randint(0, 5),
                },
            )
            customer_objs.append(customer)

        # Match mockData specific customer histories
        customer_objs[0].total_orders = 5
        customer_objs[0].delivered_count = 2
        customer_objs[0].rto_count = 3
        customer_objs[0].save()

        self.stdout.write(f"  ✓ {len(customer_objs)} customers created")

        # ── Addresses ──────────────────────────────────────────────────
        address_objs = []
        for i, customer in enumerate(customer_objs):
            addr_data = ADDRESSES[i]
            addr, _ = Address.objects.get_or_create(
                customer=customer,
                full_address=addr_data["full"],
                defaults={
                    "city": customer.city,
                    "suggested_address": addr_data["suggested"],
                    "confidence_score": addr_data["confidence"],
                    "status": addr_data["status"],
                    "map_preview_url": "https://via.placeholder.com/600x300",
                },
            )
            address_objs.append(addr)
        self.stdout.write(f"  ✓ {len(address_objs)} addresses created")

        # ── Orders ─────────────────────────────────────────────────────
        now = timezone.now()
        for i, o_data in enumerate(ORDERS_DATA):
            customer = customer_objs[o_data["customer_idx"]]
            address = address_objs[o_data["customer_idx"]]

            order, created = Order.objects.get_or_create(
                order_id=o_data["order_id"],
                defaults={
                    "merchant": user,
                    "customer": customer,
                    "address": address,
                    "amount": Decimal(str(o_data["amount"])),
                    "status": o_data["status"],
                    "risk_score": o_data["risk_score"],
                    "fraud_score": o_data["fraud_score"],
                    "rto_probability": o_data["rto_probability"],
                    "risk_level": o_data["risk_level"],
                    "address_score": o_data["address_score"],
                    "recommended_action": o_data["recommended_action"],
                    "chat_status": o_data["chat_status"],
                    "payment_method": "cod",
                    "source": "shopify",
                },
            )

            if created:
                # Items
                for item in o_data["items"]:
                    OrderItem.objects.create(
                        order=order,
                        name=item["name"],
                        price=Decimal(str(item["price"])),
                        qty=item["qty"],
                    )

                # Risk factors
                for rf in o_data["risk_factors"]:
                    RiskFactor.objects.create(
                        order=order,
                        name=rf["name"],
                        score=rf["score"],
                        level=rf["level"],
                    )

                # WhatsApp interaction
                WhatsAppInteraction.objects.create(
                    order=order,
                    last_message_sent=now - timedelta(hours=random.randint(1, 48)),
                    customer_response="Yes, confirm order" if o_data["chat_status"] == "confirmed" else "",
                    time_to_first_reply=f"{random.randint(1, 30)} mins",
                    nudges_sent=random.randint(0, 3),
                )

                # Conversation with messages
                convo = Conversation.objects.create(
                    order=order,
                    status="completed" if o_data["chat_status"] in ("confirmed", "denied") else "active",
                )
                Message.objects.create(
                    conversation=convo,
                    sender="bot",
                    content=f"Hi {customer.name}, please confirm your order for {', '.join(item['name'] for item in o_data['items'])}. Total: PKR {o_data['amount']}",
                )
                if o_data["chat_status"] == "confirmed":
                    Message.objects.create(
                        conversation=convo, sender="user", content="Yes"
                    )
                    Message.objects.create(
                        conversation=convo,
                        sender="bot",
                        content="Please share your location pin.",
                    )
                elif o_data["chat_status"] == "denied":
                    Message.objects.create(
                        conversation=convo, sender="user", content="No, cancel it."
                    )

        # ── Generate extra orders for richer analytics ──────────────────
        statuses = ["pending", "verified", "rejected", "delivered", "rto"]
        risk_levels = ["low", "medium", "high", "critical"]
        for j in range(6, 26):
            customer = random.choice(customer_objs)
            address = address_objs[customer_objs.index(customer)]
            oid = f"ORD-{j:03d}"
            if not Order.objects.filter(order_id=oid).exists():
                order_status = random.choice(statuses)
                risk = random.randint(5, 95)
                Order.objects.create(
                    order_id=oid,
                    merchant=user,
                    customer=customer,
                    address=address,
                    amount=Decimal(str(random.randint(500, 25000))),
                    status=order_status,
                    risk_score=risk,
                    fraud_score=random.randint(0, 100),
                    rto_probability=random.choice(["Very Low", "Low", "Medium", "High"]),
                    risk_level=random.choice(risk_levels),
                    address_score=random.randint(30, 100),
                    recommended_action=random.choice(["ship_order", "verify_address", "call_customer", "cancel_order"]),
                    chat_status=random.choice(["confirmed", "unverified", "denied", "no_response"]),
                    payment_method="cod",
                    source=random.choice(["shopify", "manual"]),
                    created_at=now - timedelta(days=random.randint(0, 30)),
                )
                OrderItem.objects.create(
                    order=Order.objects.get(order_id=oid),
                    name=random.choice(["Phone Case", "Headphones", "Charger", "Laptop Stand", "USB Cable"]),
                    price=Decimal(str(random.randint(200, 5000))),
                    qty=random.randint(1, 3),
                )

        self.stdout.write(self.style.SUCCESS(
            "\n✅ Seed complete! 25 orders, 10 customers, conversations, and analytics data created."
        ))
        self.stdout.write(self.style.SUCCESS(
            "   Login: demo@riskguard.pk / RiskGuard@2024"
        ))

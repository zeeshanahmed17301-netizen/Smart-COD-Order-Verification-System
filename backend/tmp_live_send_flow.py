from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.customers.models import Customer
from apps.addresses.models import Address
from apps.orders.models import Order, OrderItem, OrderSourceSnapshot
from apps.risk_engine.services import RiskScoringEngine
from apps.chatbot.models import Conversation, Message


phone = "03449173430"

User = get_user_model()
merchant = User.objects.filter(id=1).first() or User.objects.first()

customer, _ = Customer.objects.get_or_create(
    merchant=merchant,
    phone=phone,
    defaults={
        "name": "Live Pakistan Test",
        "email": "",
        "city": "Lahore",
    },
)
customer.name = "Live Pakistan Test"
customer.city = "Lahore"
customer.total_orders = max(customer.total_orders, 7)
customer.delivered_count = max(customer.delivered_count, 1)
customer.rto_count = max(customer.rto_count, 5)
customer.ghosted_count = max(customer.ghosted_count, 2)
customer.save()

address, _ = Address.objects.get_or_create(
    customer=customer,
    full_address="Near Bhatta Chowk, Lahore",
    defaults={
        "city": "Lahore",
        "district": "",
        "province": "Punjab",
        "postal_code": "54000",
        "status": "partial",
        "confidence_score": 40,
        "area_rto_rate": 35,
        "is_high_risk_area": True,
    },
)
address.city = "Lahore"
address.district = ""
address.status = "partial"
address.confidence_score = 40
address.area_rto_rate = 35
address.is_high_risk_area = True
address.save()

order_id = f"LIVE-PK-{timezone.now().strftime('%H%M%S%f')}"
order = Order.objects.create(
    order_id=order_id,
    merchant=merchant,
    customer=customer,
    address=address,
    amount=Decimal("12990.00"),
    payment_method="cod",
    status="pending",
    source="shopify",
    chat_status="no_response",
)
OrderItem.objects.create(
    order=order,
    name="Premium Gadget",
    price=Decimal("4330.00"),
    qty=3,
    category="electronics",
)
OrderSourceSnapshot.objects.create(
    order=order,
    source_name="facebook_ad",
    client_ip="203.0.113.44",
    browser_ip="203.0.113.44",
    billing_matches_shipping=False,
    shopify_risk_recommendation="INVESTIGATE",
    shopify_risk_level="HIGH",
)

result = RiskScoringEngine.score_and_save(order)
conversation = Conversation.objects.filter(order=order).first()
first_message = (
    Message.objects.filter(conversation=conversation, sender="bot")
    .order_by("timestamp")
    .first()
    if conversation
    else None
)

print("order_id=", order.order_id)
print(
    "risk=",
    result.risk_level,
    "action=",
    result.recommended_action,
    "fraud=",
    result.fraud_score,
    "rto=",
    result.rto_probability_score,
)
print(
    "conversation=",
    conversation.status if conversation else None,
    "missing=",
    conversation.missing_fields if conversation else None,
)
print("message_sid=", first_message.message_sid if first_message else None)
print("message_preview=", first_message.content[:180] if first_message else None)

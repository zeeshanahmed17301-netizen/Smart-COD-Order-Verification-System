import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["PYTHONIOENCODING"] = "utf8"
django.setup()

from apps.orders.models import Order, OrderSourceSnapshot
from apps.risk_engine.services import RiskScoringEngine
from apps.customers.models import Customer
from apps.addresses.models import Address
from apps.accounts.models import User
from unittest.mock import patch

def mock_send_whatsapp(*args, **kwargs):
    to = kwargs.get("to_phone") or (args[0] if args else "Unknown")
    body = kwargs.get("body") or (args[1] if len(args) > 1 else "Unknown")
    print(f"\n\033[92m[WHATSAPP AUTOMATICALLY TRIGGERED explicitly to {to}]:\033[0m\n{body}\n")
    return "MOCK_SID_12345"

def run_simulation():
    merchant = User.objects.filter(is_superuser=True).first() or User.objects.first()
    
    import random
    unique_suffix = random.randint(1000, 9999)
    test_phone = f"+9230000{unique_suffix}"
    ip_address = f"203.0.{random.randint(1, 250)}.{random.randint(1, 250)}"
    
    # Create test customer and address
    customer, _ = Customer.objects.get_or_create(
        phone=test_phone,
        merchant=merchant,
        defaults={"email": f"velocity_{unique_suffix}@example.com", "name": "Rapid Buyer Example"}
    )
    address, _ = Address.objects.get_or_create(
        customer=customer,
        full_address="123 Missing Area Street",
        city="Test City Unknown",
        defaults={}
    )
    
    print("="*70)
    print("STARTING E2E VELOCITY & ADDRESS RISK SIMULATION")
    print("="*70)
    print("Scenario: A Single IP/Phone combination will place 3 rapid high-risk COD orders.")
    print("We should see the fraud score remain low on Order 1, jump dynamically, and auto-trigger Twilio!\n")
    
    with patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", side_effect=mock_send_whatsapp):
        for i in range(1, 4):
            print(f"\n[-] Constructing Incoming Order #{i}...")
            order = Order.objects.create(
                order_id=f"SIMULATION-ORDER-{i}-{int(timezone.now().timestamp())}",
                merchant=merchant,
                customer=customer,
                address=address,
                amount=Decimal("2500.00"),
                payment_method="cod",
                status="pending"
            )
            # Mock the network footprint representing identical source
            source = OrderSourceSnapshot.objects.create(
                order=order,
                client_ip=ip_address,
                browser_ip=ip_address
            )
            
            from apps.risk_engine.enrichment import OrderEnrichmentService
            OrderEnrichmentService.enrich(order)
            
            # Feed into Risk scoring engine natively!
            print(f"[*] Running Risk Scoring Engine Sequence for #{i}...")
            RiskScoringEngine.score_and_save(order)
            
            # Check Results
            order.refresh_from_db()
            print(f"[>] Fraud Score:       \033[93m{order.fraud_score}\033[0m points")
            print(f"[>] RTO Score:         \033[93m{order.rto_probability_score}\033[0m points")
            print(f"[>] Address Score:     \033[93m{order.address_score}\033[0m %")
            print(f"[>] Chatbot State:     {order.chat_status}")
            print("-" * 50)

if __name__ == "__main__":
    run_simulation()

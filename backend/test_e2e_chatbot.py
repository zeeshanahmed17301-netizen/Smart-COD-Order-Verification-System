import os
import json
import django
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch

# Set up Django environment manually
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["PYTHONIOENCODING"] = "utf8"
django.setup()

from apps.orders.models import Order, OrderSourceSnapshot
from apps.risk_engine.services import RiskScoringEngine
from apps.risk_engine.enrichment import OrderEnrichmentService
from apps.customers.models import Customer
from apps.addresses.models import Address
from apps.accounts.models import User
from apps.chatbot.services import ConversationService
from apps.chatbot.models import Conversation, Message


def mock_send_whatsapp(*args, **kwargs):
    """Instead of sending to Twilio API, print it to the console!"""
    to = kwargs.get("to_phone") or (args[0] if args else "Unknown")
    body = kwargs.get("body") or (args[1] if len(args) > 1 else "Unknown")

    print(f"\n\033[92m[BOT automatically says to {to}]:\033[0m\n{body}")
    return "MOCK_SID_12345"


def print_debug(conv):
    """Print the current conversation state for debugging."""
    conv.refresh_from_db()
    last_user_msg = (
        Message.objects.filter(conversation=conv, sender="user")
        .order_by("-timestamp")
        .first()
    )
    if last_user_msg and last_user_msg.parsed_data:
        parsed = last_user_msg.parsed_data
        print(f"\033[90m  [DEBUG] LLM intent={parsed.get('intent', '?')}, extracted={parsed}\033[0m")

    print(f"\033[90m  [DEBUG] missing_fields={conv.missing_fields}\033[0m")
    print(f"\033[90m  [DEBUG] status={conv.status}, turn={conv.turn_count}\033[0m")


def run_e2e_simulation():
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
    print("STARTING INTERACTIVE E2E SIMULATION")
    print("Risk Engine -> Automatic Evaluation -> Chatbot Fallback")
    print("="*70)

    # Clean existing conv for this order phone just in case
    # Find orders for this customer and delete their conversations
    orders_for_cust = Order.objects.filter(customer=customer)
    Conversation.objects.filter(order__in=orders_for_cust).delete()
    
    print(f"\n[-] 1. Constructing Incoming Order...")
    order = Order.objects.create(
        order_id=f"SIMULATION-ORDER-1-{int(timezone.now().timestamp())}",
        merchant=merchant,
        customer=customer,
        address=address,
        amount=Decimal("4500.00"),
        payment_method="cod",
        status="pending"
    )
    # Mock the network footprint
    OrderSourceSnapshot.objects.create(
        order=order,
        client_ip=ip_address,
        browser_ip=ip_address
    )
    
    OrderEnrichmentService.enrich(order)

    # Execute Risk Engine - this should automatically trigger Twilio mocking!
    with patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", side_effect=mock_send_whatsapp):
        print(f"[*] 2. Running Risk Scoring Engine...")
        RiskScoringEngine.score_and_save(order)
        
        order.refresh_from_db()
        print(f"[>] Fraud Score:       \033[93m{order.fraud_score}\033[0m points")
        print(f"[>] RTO Score:         \033[93m{order.rto_probability_score}\033[0m points")
        print(f"[>] Address Score:     \033[93m{order.address_score}\033[0m %")
        print(f"[>] Chatbot State:     {order.chat_status}")
        print("-" * 50)
        
        # Check if conversation started automatically
        conv = Conversation.objects.filter(order=order).first()
        if not conv:
            print("Risk threshold wasn't met to auto-trigger the bot on Order 1. Let's try scoring a second order (velocity trigger)...")
            
            # create second one quickly to trip velocity rule
            order2 = Order.objects.create(
                order_id=f"SIMULATION-ORDER-2-{int(timezone.now().timestamp())}",
                merchant=merchant, customer=customer, address=address,
                amount=Decimal("4500.00"), payment_method="cod", status="pending"
            )
            OrderSourceSnapshot.objects.create(order=order2, client_ip=ip_address, browser_ip=ip_address)
            OrderEnrichmentService.enrich(order2)
            RiskScoringEngine.score_and_save(order2)
            order2.refresh_from_db()
            
            print(f"[>] Fraud Score:       \033[93m{order2.fraud_score}\033[0m points")
            conv = Conversation.objects.filter(order=order2).first()
            order = order2

        if not conv:
            print("Failed to auto-trigger conversation.")
            return

        print(f"\n[*] 3. Auto-Trigger Successful. Entering Interactive Chat Loop!")
        print(f"\033[90m  [DEBUG] initial missing_fields={conv.missing_fields}\033[0m")
        print("\n(Type 'exit' to quit simulation. Reply '2' to test cancel, or reply with an address update.)")

        # Interactive loop
        while conv.status in ["awaiting_reply", "processing"]:
            user_reply = input("\n\033[94m[YOUR REPLY]:\033[0m ")
            if user_reply.strip().lower() == "exit":
                break

            # Process reply
            ConversationService.handle_incoming_reply(
                phone=order.customer.phone,
                body=user_reply,
                message_sid="MOCK_INCOMING_SID",
            )

            # Re-fetch after processing
            print_debug(conv)
            conv.refresh_from_db()
            order.refresh_from_db()
            
            # If the user confirmed and the conversation resolved
            if conv.status == "completed":
                print("\n[*] 4. Conversation Completed! Re-scoring Order after User resolved Missing Variables...")
                RiskScoringEngine.score_and_save(order)
                order.refresh_from_db()
                order.address.refresh_from_db()
                
                print("\n" + "="*50)
                print("E2E COMPLETE - FINAL DB STATE")
                print("="*50)
                print(f"[>] Order Status:      \033[93m{order.status}\033[0m")
                print(f"[>] Updated Address:   \033[93m{order.address.full_address}\033[0m")
                print(f"[>] New Fraud Score:   \033[93m{order.fraud_score}\033[0m")
                print(f"[>] New RTO Score:     \033[93m{order.rto_probability_score}\033[0m")
                print(f"[>] New Address Score: \033[93m{order.address_score}\033[0m")
                break
        
        if order.status == "cancelled":
             print("\n" + "="*50)
             print("E2E COMPLETE - ORDER CANCELLED BY USER")
             print("="*50)
             print(f"[>] Order Status:      \033[93m{order.status}\033[0m")

if __name__ == "__main__":
    run_e2e_simulation()

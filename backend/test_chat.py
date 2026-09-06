import os
import json
import django
from unittest.mock import patch

# Set up Django environment manually
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["PYTHONIOENCODING"] = "utf8"
django.setup()

from apps.orders.models import Order
from apps.chatbot.services import ConversationService
from apps.chatbot.models import Conversation, Message


def mock_send_whatsapp(*args, **kwargs):
    """Instead of sending to Twilio API, print it to the console!"""
    to = kwargs.get("to_phone") or (args[0] if args else "Unknown")
    body = kwargs.get("body") or (args[1] if len(args) > 1 else "Unknown")

    print(f"\n\033[92m[BOT says to {to}]:\033[0m\n{body}")
    return "MOCK_SID_12345"


def print_debug(conv):
    """Print the current conversation state for debugging."""
    conv.refresh_from_db()

    # Get the last user message's parsed data
    last_user_msg = (
        Message.objects.filter(conversation=conv, sender="user")
        .order_by("-timestamp")
        .first()
    )
    if last_user_msg and last_user_msg.parsed_data:
        parsed = last_user_msg.parsed_data
        intent = parsed.get("intent", "?")
        confidence = parsed.get("confidence", 0)
        extracted = {
            k: v
            for k, v in parsed.items()
            if k in ("city", "area", "street", "house", "landmark") and v
        }
        print(f"\033[90m  [DEBUG] LLM intent={intent}, confidence={confidence}, extracted={extracted}\033[0m")

    print(f"\033[90m  [DEBUG] collected_data={json.dumps(conv.collected_data, ensure_ascii=False)}\033[0m")
    print(f"\033[90m  [DEBUG] missing_fields={conv.missing_fields}\033[0m")
    print(f"\033[90m  [DEBUG] status={conv.status}, turn={conv.turn_count}\033[0m")


def run_test():
    # Delete previous chats
    Conversation.objects.all().delete()

    # Grab an order
    order = Order.objects.select_related("customer", "address", "merchant").first()

    # Reliably clear the district to simulate missing "area"
    order.address.district = ""
    order.address.save(update_fields=["district"])

    # Verify it was actually cleared
    order.address.refresh_from_db()
    print(f"\033[90m[SETUP] address.city='{order.address.city}', "
          f"address.district='{order.address.district}', "
          f"full_address='{order.address.full_address[:60]}...'\033[0m")

    print("=" * 60)
    print("STARTING TERMINAL CHATBOT SIMULATION (Bypassing Twilio)")
    print("=" * 60)

    # We patch TwilioService so it never makes real API calls
    with patch(
        "apps.chatbot.twilio_service.TwilioService.send_whatsapp",
        side_effect=mock_send_whatsapp,
    ):
        # Start conversation
        conv = ConversationService.start_conversation(
            order, purpose="address_verification"
        )

        if not conv or conv.status == "failed":
            print("Failed to start conversation!")
            return

        print(f"\033[90m  [DEBUG] initial missing_fields={conv.missing_fields}\033[0m")
        print("\n(Type 'exit' to quit simulation)")

        # Interactive loop
        while conv.status in ["awaiting_reply", "processing"]:
            user_reply = input("\n\033[94m[YOUR REPLY]:\033[0m ")
            if user_reply.strip().lower() == "exit":
                break

            # Send your reply straight into the backend Webhook logic
            ConversationService.handle_incoming_reply(
                phone=order.customer.phone,
                body=user_reply,
                message_sid="MOCK_INCOMING_SID",
            )

            # Print debug info and refresh conversation state
            print_debug(conv)
            conv.refresh_from_db()

        print(
            f"\n\033[93m--- SIMULATION ENDED (Status: {conv.status}) ---\033[0m"
        )
        print(f"Final missing fields: {conv.missing_fields}")
        print(f"Final collected data: {json.dumps(conv.collected_data, ensure_ascii=False)}")


if __name__ == "__main__":
    run_test()

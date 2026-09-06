from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.addresses.models import Address
from apps.chatbot.models import ChatbotSettings
from apps.chatbot.services import ConversationService
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem

User = get_user_model()


class ConversationServiceTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			email="chatbot-merchant@example.com",
			username="chatbot_merchant",
			first_name="Chatbot",
			last_name="Merchant",
			password="StrongPass123!",
		)
		ChatbotSettings.objects.create(
			merchant=self.user,
			is_connected=True,
			language="urdu",
		)
		self.customer = Customer.objects.create(
			merchant=self.user,
			name="Rapid Buyer",
			phone="+923001234567",
			email="buyer@example.com",
			city="Karachi",
		)
		self.address = Address.objects.create(
			customer=self.customer,
			full_address="123 Missing Area Street",
			city="Karachi",
			district="",
			status="partial",
			confidence_score=55,
		)
		self.order = Order.objects.create(
			order_id="ORD-CHATBOT-001",
			merchant=self.user,
			customer=self.customer,
			address=self.address,
			amount=Decimal("2500.00"),
			chat_status="unverified",
		)
		OrderItem.objects.create(
			order=self.order,
			name="Headphones",
			price=Decimal("2500.00"),
			qty=1,
			category="electronics",
		)

	def test_confidence_normalization_handles_fraction_and_percent(self):
		self.assertEqual(ConversationService._confidence_to_percent(0.8), 80.0)
		self.assertEqual(ConversationService._confidence_to_percent(80), 80.0)
		self.assertEqual(ConversationService._confidence_to_percent("0.55"), 55.0)

	def test_build_order_context_uses_order_default_for_empty_items(self):
		order_without_items = Order.objects.create(
			order_id="ORD-CHATBOT-002",
			merchant=self.user,
			customer=self.customer,
			address=self.address,
			amount=Decimal("1400.00"),
			chat_status="unverified",
		)

		context = ConversationService._build_order_context(order_without_items)

		self.assertEqual(context["items"], "order")

	@patch("apps.chatbot.services.DeepSeekClient.extract_address")
	@patch("apps.chatbot.services.DeepSeekClient.generate_message", return_value="Follow-up prompt")
	@patch("apps.chatbot.services.TwilioService.send_whatsapp", return_value="MOCK_SID")
	def test_incoming_e164_reply_matches_local_pk_phone(
		self,
		_mock_send,
		_mock_generate,
		mock_extract,
	):
		self.customer.phone = "03001234567"
		self.customer.save(update_fields=["phone"])

		conversation = ConversationService.start_conversation(
			self.order,
			purpose="address_verification",
		)
		self.assertIsNotNone(conversation)

		mock_extract.return_value = {
			"city": "",
			"area": "",
			"street": "",
			"house": "",
			"landmark": "",
			"postal_code": "",
			"full_address": "",
			"confidence": 0.0,
			"intent": "unclear",
			"needs_followup": True,
			"missing": ["area"],
		}

		result = ConversationService.handle_incoming_reply(
			phone="whatsapp:+923001234567",
			body="nahi",
			message_sid="INCOMING_SID",
		)

		conversation.refresh_from_db()

		self.assertEqual(result["status"], "followup_sent")
		self.assertEqual(conversation.status, "awaiting_reply")
		self.assertEqual(conversation.messages.filter(sender="user").count(), 1)
		self.assertEqual(
			conversation.messages.filter(sender="user").latest("timestamp").content,
			"nahi",
		)

	@patch("apps.chatbot.services.ConversationService._rescore_order")
	@patch("apps.chatbot.services.DeepSeekClient.chat", return_value="Shukriya! Aapka order confirm ho gaya hai.")
	@patch("apps.chatbot.services.DeepSeekClient.extract_address")
	@patch("apps.chatbot.services.DeepSeekClient.generate_message", return_value="Initial verification prompt")
	@patch("apps.chatbot.services.TwilioService.send_whatsapp", return_value="MOCK_SID")
	def test_fractional_confidence_allows_completion_when_missing_resolved(
		self,
		_mock_send,
		_mock_generate,
		mock_extract,
		_mock_chat,
		_mock_rescore,
	):
		conversation = ConversationService.start_conversation(
			self.order,
			purpose="address_verification",
		)
		self.assertIsNotNone(conversation)

		conversation.step = 3
		conversation.missing_fields = ["area"]
		conversation.collected_data = {}
		conversation.save(update_fields=["step", "missing_fields", "collected_data"])

		mock_extract.return_value = {
			"city": "Karachi",
			"area": "Gulshan",
			"street": "",
			"house": "",
			"landmark": "Madina Masjid",
			"postal_code": "",
			"full_address": "Gulshan, Karachi",
			"confidence": 0.8,
			"intent": "address_update",
			"needs_followup": False,
			"missing": [],
		}

		result = ConversationService.handle_incoming_reply(
			phone=self.customer.phone,
			body="Gulshan Karachi",
			message_sid="INCOMING_SID",
		)

		conversation.refresh_from_db()
		self.order.refresh_from_db()

		self.assertEqual(result["status"], "completed")
		self.assertEqual(conversation.status, "completed")
		self.assertEqual(conversation.missing_fields, [])
		self.assertEqual(self.order.chat_status, "confirmed")

	@patch("apps.chatbot.services.DeepSeekClient.chat", return_value="Order cancel note.")
	@patch("apps.chatbot.services.DeepSeekClient.generate_message", return_value="Initial verification prompt")
	@patch("apps.chatbot.services.TwilioService.send_whatsapp", return_value="MOCK_SID")
	def test_customer_cancellation_updates_order_lifecycle(
		self,
		_mock_send,
		_mock_generate,
		_mock_chat,
	):
		conversation = ConversationService.start_conversation(
			self.order,
			purpose="address_verification",
		)
		self.assertIsNotNone(conversation)

		result = ConversationService._handle_cancellation(conversation, self.order)

		conversation.refresh_from_db()
		self.order.refresh_from_db()
		self.customer.refresh_from_db()

		self.assertEqual(result["status"], "cancelled")
		self.assertEqual(conversation.status, "cancelled")
		self.assertEqual(self.order.status, "cancelled")
		self.assertEqual(self.order.chat_status, "denied")
		self.assertEqual(self.order.recommended_action, "cancel_order")
		self.assertEqual(self.customer.cancelled_count, 1)

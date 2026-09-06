from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.addresses.models import Address
from apps.chatbot.models import Conversation, Message, WhatsAppInteraction
from apps.customers.models import Customer

from .models import Order, OrderEnrichment, OrderItem, OrderSourceSnapshot, RiskFactor

User = get_user_model()


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class OrderDetailContractTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            username="merchant",
            first_name="Merchant",
            last_name="User",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="other",
            first_name="Other",
            last_name="User",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)

        self.customer = Customer.objects.create(
            merchant=self.user,
            name="Ahmed Khan",
            phone="+923001234567",
            email="ahmed@example.com",
            city="Karachi",
            total_orders=5,
            delivered_count=4,
            rto_count=1,
        )
        self.address = Address.objects.create(
            customer=self.customer,
            full_address="123 Street, Karachi",
            city="Karachi",
            suggested_address="123 Street, DHA, Karachi",
            confidence_score=88,
            status="valid",
        )
        self.order = Order.objects.create(
            order_id="ORD-1001",
            merchant=self.user,
            customer=self.customer,
            address=self.address,
            amount=Decimal("2500.00"),
            payment_method="cod",
            risk_score=67,
            fraud_score=42,
            rto_probability_score=44,
            score_calibration_version="v1.2",
            risk_level="medium",
            address_score=88,
            rto_probability="Medium",
            recommended_action="verify_address",
            chat_status="confirmed",
        )
        OrderSourceSnapshot.objects.create(
            order=self.order,
            shopify_order_gid="gid://shopify/Order/1001",
            shopify_legacy_order_id="1001",
            client_ip="203.0.113.10",
            browser_ip="203.0.113.10",
            user_agent="Mozilla/5.0",
            session_hash="sess_123",
            source_name="facebook_ad",
            source_identifier="fb-campaign-1",
            financial_status="pending",
            fulfillment_status="unfulfilled",
            billing_matches_shipping=True,
            shopify_risk_recommendation="INVESTIGATE",
            shopify_risk_level="HIGH",
            shopify_risk_payload={"risk": {"recommendation": "INVESTIGATE"}},
            raw_order_payload={
                "id": 1001,
                "name": "#1001",
                "order_number": 1003,
                "confirmation_number": "851KLKVRT",
                "confirmed": True,
                "contact_email": "mian@example.com",
                "email": None,
                "phone": None,
                "buyer_accepts_marketing": True,
                "currency": "PKR",
                "current_subtotal_price": "1699.00",
                "current_subtotal_price_set": {
                    "shop_money": {"amount": "1699.00", "currency_code": "PKR"},
                    "presentment_money": {"amount": "1699.00", "currency_code": "PKR"},
                },
                "current_total_discounts": "0.00",
                "current_total_discounts_set": {
                    "shop_money": {"amount": "0.00", "currency_code": "PKR"},
                    "presentment_money": {"amount": "0.00", "currency_code": "PKR"},
                },
                "current_total_price": "1699.00",
                "current_total_price_set": {
                    "shop_money": {"amount": "1699.00", "currency_code": "PKR"},
                    "presentment_money": {"amount": "1699.00", "currency_code": "PKR"},
                },
                "total_tax": "0.00",
                "total_tax_set": {
                    "shop_money": {"amount": "0.00", "currency_code": "PKR"},
                    "presentment_money": {"amount": "0.00", "currency_code": "PKR"},
                },
                "financial_status": "pending",
                "fulfillment_status": "unfulfilled",
                "browser_ip": "39.48.26.209",
                "note_attributes": [
                    {"name": "First name", "value": "Mian zain"},
                    {"name": "Last name", "value": "Ali"},
                    {"name": "Phone number", "value": "03180911060"},
                ],
                "shipping_address": {
                    "first_name": "Mian zain",
                    "last_name": "Ali",
                    "phone": "+923180911060",
                    "address1": "COMSATS",
                    "city": "Abbottabad",
                    "province": "Khyber Pakhtunkhwa",
                    "country": "Pakistan",
                },
                "billing_address": {
                    "first_name": "Mian zain",
                    "last_name": "Ali",
                    "phone": "+923180911060",
                    "address1": "COMSATS",
                    "city": "Abbottabad",
                    "province": "Khyber Pakhtunkhwa",
                    "country": "Pakistan",
                },
                "customer": {
                    "id": 55,
                    "first_name": "Mian zain",
                    "last_name": "Ali",
                    "phone": "+923180911060",
                    "orders_count": 1,
                    "state": "enabled",
                },
                "shipping_lines": [
                    {"title": "Free shipping", "price": "0.00"},
                ],
                "tags": ["vip", "cod"],
            },
        )
        OrderEnrichment.objects.create(
            order=self.order,
            address_provider="internal",
            address_validation_status="valid",
            normalized_address="123 Street, DHA, Karachi",
            address_confidence=88,
            address_precision="premise",
            ip_provider="shopify",
            ip_risk_score=50,
            repeat_ip_orders_7d=2,
            repeat_ip_customers_30d=1,
            repeat_phone_orders_30d=5,
            repeat_address_orders_30d=3,
            source_rto_rate=22,
            area_rto_rate=18,
            customer_rto_rate=20,
            category_rto_rate=12,
            contactability_score=95,
            enrichment_status="completed",
        )
        OrderItem.objects.create(order=self.order, name="Phone Case", price=Decimal("1250.00"), qty=2)
        RiskFactor.objects.create(order=self.order, name="Repeat cancellation history", score=55, level="medium")
        conversation = Conversation.objects.create(order=self.order, status="completed")
        Message.objects.create(conversation=conversation, sender="bot", content="Please confirm your order.")
        Message.objects.create(conversation=conversation, sender="user", content="Confirmed.")
        WhatsAppInteraction.objects.create(
            order=self.order,
            customer_response="Confirmed",
            time_to_first_reply="2m",
            nudges_sent=1,
        )

    def test_order_detail_returns_frontend_compatible_payload(self):
        response = self.client.get(f"/api/orders/{self.order.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], self.order.order_id)
        self.assertEqual(response.data["payment_method"], "cod")
        self.assertEqual(response.data["customer"]["name"], "Ahmed Khan")
        self.assertEqual(response.data["address"]["full_address"], "123 Street, Karachi")
        self.assertEqual(response.data["items"][0]["name"], "Phone Case")
        self.assertEqual(response.data["risk_factors"][0]["name"], "Repeat cancellation history")
        self.assertEqual(response.data["chat_log"][0]["sender"], "bot")
        self.assertEqual(response.data["whatsapp_interaction"]["customer_response"], "Confirmed")
        self.assertIn("order", response.data)
        self.assertIn("risk_analysis", response.data)
        self.assertIn("address_verification", response.data)
        self.assertIn("canonical_facts", response.data)
        self.assertIn("rto_probability_score", response.data)
        self.assertEqual(response.data["source_snapshot"]["order_ip"], "203.0.113.10")
        self.assertEqual(response.data["source_snapshot"]["order_ip_source"], "client_ip")
        self.assertNotIn("client_ip", response.data["source_snapshot"])
        self.assertNotIn("browser_ip", response.data["source_snapshot"])
        self.assertEqual(response.data["source_snapshot"]["shopify_risk_recommendation"], "INVESTIGATE")
        self.assertEqual(response.data["source_snapshot"]["raw_order_payload"]["name"], "#1001")
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["customer"]["name"],
            "Mian zain Ali",
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["order_identity"]["confirmed"],
            True,
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["customer"]["contact_email"],
            "mian@example.com",
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["additional_details"]["order_ip"],
            "203.0.113.10",
        )
        self.assertNotIn(
            "client_ip",
            response.data["source_snapshot"]["shopify_details"]["additional_details"],
        )
        self.assertNotIn(
            "browser_ip",
            response.data["source_snapshot"]["shopify_details"]["additional_details"],
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["payment"]["financial_status"],
            "pending",
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["payment"]["subtotal_price_set"]["shop_money"]["amount"],
            "1699.00",
        )
        self.assertEqual(
            response.data["source_snapshot"]["shopify_details"]["addresses"]["shipping_address"]["city"],
            "Abbottabad",
        )
        self.assertEqual(
            response.data["canonical_facts"]["customer"]["name"],
            "Mian zain Ali",
        )
        self.assertEqual(
            response.data["canonical_facts"]["customer"]["phone"],
            "+923180911060",
        )
        self.assertEqual(
            response.data["canonical_facts"]["customer"]["email"],
            "mian@example.com",
        )
        self.assertEqual(
            response.data["canonical_facts"]["source"]["name"],
            "facebook_ad",
        )
        self.assertEqual(
            response.data["canonical_facts"]["addresses"]["shipping_address"]["city"],
            "Abbottabad",
        )
        self.assertEqual(
            response.data["canonical_facts"]["network"]["order_ip"],
            "203.0.113.10",
        )
        self.assertEqual(
            response.data["canonical_facts"]["notes"]["important_attributes"][0]["key"],
            "first_name",
        )
        self.assertEqual(response.data["enrichment"]["ip_risk_score"], 50)
        self.assertIn("score_breakdown", response.data)
        self.assertIn("decision_summary", response.data)
        self.assertIn("information_quality", response.data)
        self.assertGreaterEqual(response.data["information_quality"]["coverage_score"], 80)
        self.assertNotIn(
            "Customer phone number is missing.",
            response.data["information_quality"]["warnings"],
        )
        self.assertNotIn(
            "Billing and shipping consistency could not be confirmed.",
            response.data["information_quality"]["warnings"],
        )
        self.assertEqual(response.data["decision_summary"]["primary_driver"], "Repeat cancellation history")
        self.assertEqual(response.data["score_breakdown"]["operational"]["source_rto_rate"], 22)
        self.assertEqual(response.data["score_breakdown"]["calibration"]["version"], "v1.2")
        self.assertIn("probability", response.data["score_breakdown"]["fraud"])
        self.assertIn("confidence_interval", response.data["score_breakdown"]["fraud"])
        self.assertIn("probability", response.data["score_breakdown"]["rto"])
        self.assertEqual(
            sorted(response.data["score_breakdown"]["fraud"]["confidence_interval"].keys()),
            ["lower", "upper"],
        )

    def test_order_list_returns_canonical_customer_fields(self):
        response = self.client.get("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]
        self.assertEqual(row["customer_name"], "Mian zain Ali")
        self.assertEqual(row["customer_phone"], "+923180911060")
        self.assertEqual(row["customer_city"], "Abbottabad")
        self.assertIn("fraud_probability", row)
        self.assertIn("fraud_confidence_interval", row)
        self.assertIn("rto_probability_percent", row)
        self.assertIn("rto_confidence_interval", row)
        self.assertIn("courier_coverage_score", row)
        self.assertIn("courier_match_confidence", row)
        self.assertEqual(row["chat_status"], "completed")

    def test_order_list_city_filter_matches_canonical_city(self):
        response = self.client.get("/api/orders/?city=Abbottabad")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["order_id"], "ORD-1001")

    def test_order_detail_is_scoped_to_authenticated_merchant(self):
        other_customer = Customer.objects.create(
            merchant=self.other_user,
            name="Hidden User",
            phone="+923009999999",
            city="Lahore",
        )
        hidden_order = Order.objects.create(
            order_id="ORD-HIDDEN",
            merchant=self.other_user,
            customer=other_customer,
            amount=Decimal("1000.00"),
        )

        response = self.client.get(f"/api/orders/{hidden_order.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", return_value="TEST_SID")
    def test_order_create_scores_order_and_updates_customer_history(self, send_whatsapp_mock, auto_trigger_mock):
        response = self.client.post(
            "/api/orders/",
            {
                "order_id": "ORD-CREATE-1",
                "customer": self.customer.id,
                "address": self.address.id,
                "amount": "3100.00",
                "payment_method": "cod",
                "source": "manual",
                "campaign": "landing-page",
                "items": [
                    {
                        "name": "Charger",
                        "price": "1550.00",
                        "qty": 2,
                        "sku": "CH-1",
                        "category": "accessories",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_order = Order.objects.select_related("customer", "enrichment").get(
            order_id="ORD-CREATE-1"
        )
        self.customer.refresh_from_db()

        self.assertIsNotNone(created_order.risk_score)
        self.assertGreaterEqual(created_order.address_score, 0)
        self.assertIsNotNone(created_order.enrichment)
        self.assertIn(created_order.enrichment.enrichment_status, {"completed", "partial", "failed"})
        self.assertTrue(created_order.score_calibration_version)
        self.assertTrue(created_order.risk_level)
        self.assertTrue(created_order.recommended_action)
        self.assertEqual(self.customer.total_orders, 6)
        auto_trigger_mock.assert_called_once()
        send_whatsapp_mock.assert_not_called()


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class OrderActionEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="actions@example.com",
            username="actions",
            first_name="Action",
            last_name="User",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)

        self.customer = Customer.objects.create(
            merchant=self.user,
            name="Action Customer",
            phone="03124590876",
            city="Lahore",
        )
        self.address = Address.objects.create(
            customer=self.customer,
            full_address="House 10, Street 2, Model Town, Lahore",
            city="Lahore",
            district="Model Town",
            province="Punjab",
            postal_code="54000",
            confidence_score=82,
            status="valid",
        )

    def create_order(self, order_id):
        return Order.objects.create(
            order_id=order_id,
            merchant=self.user,
            customer=self.customer,
            address=self.address,
            amount=Decimal("1800.00"),
            payment_method="cod",
            status="pending",
            chat_status="unverified",
        )

    def test_accept_marks_order_verified(self):
        order = self.create_order("ORD-ACTION-ACCEPT")

        response = self.client.post(f"/api/orders/{order.id}/accept/")

        order.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order.status, "verified")

    @patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", return_value="TEST_SID")
    @patch("apps.chatbot.services.ConversationService.send_admin_confirmation_message")
    def test_confirm_marks_order_verified_and_sends_message(self, send_confirmation_mock, send_whatsapp_mock):
        order = self.create_order("ORD-ACTION-CONFIRM")

        response = self.client.post(f"/api/orders/{order.id}/confirm/")

        order.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order.status, "verified")
        send_confirmation_mock.assert_called_once_with(order)
        send_whatsapp_mock.assert_not_called()

    @patch("apps.chatbot.twilio_service.TwilioService.send_whatsapp", return_value="TEST_SID")
    @patch("apps.chatbot.services.ConversationService.send_admin_cancellation_message")
    def test_cancel_and_legacy_reject_cancel_order(self, send_cancellation_mock, send_whatsapp_mock):
        cancel_order = self.create_order("ORD-ACTION-CANCEL")
        reject_order = self.create_order("ORD-ACTION-REJECT")

        cancel_response = self.client.post(f"/api/orders/{cancel_order.id}/cancel/")
        reject_response = self.client.post(f"/api/orders/{reject_order.id}/reject/")

        cancel_order.refresh_from_db()
        reject_order.refresh_from_db()
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_order.status, "cancelled")
        self.assertEqual(cancel_order.chat_status, "denied")
        self.assertEqual(reject_order.status, "cancelled")
        self.assertEqual(reject_order.chat_status, "denied")
        self.assertEqual(send_cancellation_mock.call_count, 2)
        self.assertEqual(send_whatsapp_mock.call_count, 2)

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.addresses.models import Address
from apps.customers.models import Customer
from apps.orders.models import Order

from .models import RiskSession, RiskTelemetryEvent

User = get_user_model()


class TelemetryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="telemetry@example.com",
            username="telemetry_user",
            first_name="Telemetry",
            last_name="User",
            password="StrongPass123!",
        )
        self.customer = Customer.objects.create(
            merchant=self.user,
            name="Telemetry Customer",
            phone="+923001112233",
            city="Karachi",
        )
        self.address = Address.objects.create(
            customer=self.customer,
            full_address="Street 1, Karachi",
            city="Karachi",
        )
        self.order = Order.objects.create(
            order_id="ORD-TELEMETRY-1",
            merchant=self.user,
            customer=self.customer,
            address=self.address,
            amount=Decimal("1500.00"),
        )

    def test_session_and_event_can_link_to_customer_and_order(self):
        session = RiskSession.objects.create(
            session_id="sess_telemetry_1",
            merchant=self.user,
            customer=self.customer,
            device_fingerprint_id="device_123",
            client_ip="203.0.113.10",
        )
        event = RiskTelemetryEvent.objects.create(
            session=session,
            order=self.order,
            event_type="checkout_started",
            schema_version="v1",
            occurred_at=self.order.created_at,
        )

        self.assertEqual(event.session, session)
        self.assertEqual(event.order, self.order)
        self.assertEqual(str(session), "sess_telemetry_1")

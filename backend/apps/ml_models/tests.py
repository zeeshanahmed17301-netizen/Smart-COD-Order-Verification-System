from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.addresses.models import Address
from apps.customers.models import Customer
from apps.orders.models import Order, OrderFeatureSnapshot

from .models import FeatureAggregateWindow, FeatureSchemaVersion

User = get_user_model()


class MlModelSupportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="mlmodels@example.com",
            username="ml_models_user",
            first_name="ML",
            last_name="Models",
            password="StrongPass123!",
        )
        self.customer = Customer.objects.create(
            merchant=self.user,
            name="Feature Customer",
            phone="+923004445556",
            city="Lahore",
        )
        self.address = Address.objects.create(
            customer=self.customer,
            full_address="Block 10, Lahore",
            city="Lahore",
        )
        self.order = Order.objects.create(
            order_id="ORD-FEATURE-1",
            merchant=self.user,
            customer=self.customer,
            address=self.address,
            amount=Decimal("2200.00"),
        )

    def test_feature_schema_snapshot_and_aggregate_window_models(self):
        schema = FeatureSchemaVersion.objects.create(
            version="fraud_v1",
            target="fraud",
            is_active=True,
            feature_names=["order_amount", "ip_risk_score"],
            required_feature_names=["order_amount"],
        )
        snapshot = OrderFeatureSnapshot.objects.create(
            order=self.order,
            feature_schema_version=schema.version,
            snapshot_type="online_scoring",
            generated_by="system",
            features={"order_amount": 2200.0, "ip_risk_score": 12.0},
            feature_hash="abc123",
        )
        aggregate = FeatureAggregateWindow.objects.create(
            entity_type="customer",
            entity_key=str(self.customer.id),
            window_name="30d",
            metrics={"order_count": 3, "rto_rate": 12.5},
            computed_at=self.order.created_at,
        )

        self.assertEqual(snapshot.order, self.order)
        self.assertEqual(snapshot.feature_schema_version, "fraud_v1")
        self.assertEqual(aggregate.window_name, "30d")

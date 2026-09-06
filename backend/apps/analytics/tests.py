from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.customers.models import Customer
from apps.orders.models import Order, OrderSourceSnapshot

User = get_user_model()


class AnalyticsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            username="merchant",
            first_name="Merchant",
            last_name="User",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)
        customer = Customer.objects.create(
            merchant=self.user,
            name="Ahmed Khan",
            phone="+923001234567",
            city="Karachi",
        )
        order_one = Order.objects.create(
            order_id="ORD-1",
            merchant=self.user,
            customer=customer,
            amount=Decimal("2500.00"),
            status="pending",
            risk_score=60,
            fraud_score=30,
            address_score=80,
            risk_level="medium",
        )
        OrderSourceSnapshot.objects.create(
            order=order_one,
            source_name="facebook_ad",
            raw_order_payload={
                "shipping_address": {
                    "city": "Abbottabad",
                    "province": "Khyber Pakhtunkhwa",
                    "address1": "COMSATS",
                }
            },
        )
        Order.objects.create(
            order_id="ORD-2",
            merchant=self.user,
            customer=customer,
            amount=Decimal("1800.00"),
            status="verified",
            risk_score=20,
            fraud_score=10,
            address_score=90,
            risk_level="low",
        )
        Order.objects.create(
            order_id="ORD-3",
            merchant=self.user,
            customer=customer,
            amount=Decimal("3200.00"),
            status="rto",
            risk_score=85,
            fraud_score=65,
            address_score=55,
            risk_level="high",
        )

    def test_savings_counts_engine_driven_cancellations(self):
        customer = Customer.objects.get(merchant=self.user)
        # Engine said cancel + admin stopped it → counts as savings.
        Order.objects.create(
            order_id="ORD-SAVED", merchant=self.user, customer=customer,
            amount=Decimal("4000.00"), status="cancelled", risk_level="high",
            recommended_action="cancel_order",
        )
        # Cancelled but the engine never recommended cancel → not attributable.
        Order.objects.create(
            order_id="ORD-CANCEL-LOW", merchant=self.user, customer=customer,
            amount=Decimal("9999.00"), status="cancelled", risk_level="low",
            recommended_action="ship_order",
        )

        response = self.client.get("/api/analytics/dashboard-stats/?days=7")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only the engine-driven cancellation contributes (4000), not the benign one.
        self.assertEqual(response.data["savings"], 4000.0)
        self.assertEqual(response.data["savingsCount"], 1)

    def test_overview_returns_expected_keys(self):
        response = self.client.get("/api/analytics/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status_breakdown", response.data)
        self.assertIn("risk_breakdown", response.data)
        self.assertIn("top_cities", response.data)
        self.assertIn("averages", response.data)
        self.assertEqual(response.data["total_orders"], 3)
        self.assertIn("risk_score", response.data["averages"])
        self.assertIn("fraud_score", response.data["averages"])
        self.assertEqual(response.data["top_cities"][0]["city"], "Karachi")
        self.assertEqual(response.data["top_cities"][1]["city"], "Abbottabad")

    def test_heatmap_and_fraud_trends_return_chart_ready_data(self):
        heatmap_response = self.client.get("/api/analytics/risk-heatmap/")
        fraud_response = self.client.get("/api/analytics/fraud-trends/?days=7")

        self.assertEqual(heatmap_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fraud_response.status_code, status.HTTP_200_OK)
        self.assertIn("city", heatmap_response.data[0])
        self.assertIn("avg_risk", heatmap_response.data[0])
        self.assertIn("avg_fraud", heatmap_response.data[0])
        self.assertEqual({entry["city"] for entry in heatmap_response.data}, {"Karachi", "Abbottabad"})
        self.assertIn("date", fraud_response.data[0])
        self.assertIn("avg_fraud", fraud_response.data[0])
        self.assertIn("order_count", fraud_response.data[0])

    def test_dashboard_stats_and_rto_trend_use_selected_period(self):
        customer = Customer.objects.get(merchant=self.user)
        old_order = Order.objects.create(
            order_id="ORD-OLD-RTO",
            merchant=self.user,
            customer=customer,
            amount=Decimal("5000.00"),
            status="rto",
            risk_score=90,
            fraud_score=80,
            address_score=40,
            risk_level="critical",
        )
        Order.objects.filter(id=old_order.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        stats_response = self.client.get("/api/analytics/dashboard-stats/?days=7")
        trend_response = self.client.get("/api/analytics/rto-trend/?days=7")

        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data["totalOrders"], 3)
        self.assertEqual(stats_response.data["rtoCount"], 1)
        self.assertEqual(stats_response.data["rtoPercentage"], 33.3)
        self.assertEqual(stats_response.data["periodDays"], 7)
        self.assertEqual(trend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(trend_response.data), 7)
        self.assertEqual(sum(day["rto_count"] for day in trend_response.data), 1)

from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch

from django.test import TestCase
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.addresses.courier_coverage import check_reachability, invalidate_coverage_cache
from apps.addresses.models import CourierBranch
from apps.orders.models import Order

from .models import APIKey, StoreConnection
from .shopify_sync import ShopifySyncError, _bootstrap_address_metadata, sync_shopify_connection
from .webhooks import ShopifyWebhookView

User = get_user_model()


class APIKeyViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            username="merchant",
            first_name="Merchant",
            last_name="User",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)

    def test_create_returns_secret_once_and_stores_hashed_secret(self):
        response = self.client.post("/api/stores/api-keys/", {"label": "Primary"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("secret", response.data)
        self.assertTrue(response.data["secret"].startswith("rg_secret_"))

        api_key = APIKey.objects.get(id=response.data["id"])
        self.assertNotEqual(api_key.secret, response.data["secret"])
        self.assertTrue(api_key.check_secret(response.data["secret"]))

    def test_list_does_not_expose_secret(self):
        api_key = APIKey.objects.create(
            merchant=self.user,
            label="Primary",
            key=APIKey.generate_key(),
            secret="",
        )
        api_key.set_secret("rg_secret_example")
        api_key.save(update_fields=["secret"])

        response = self.client.get("/api/stores/api-keys/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertIn("key", result)
        self.assertNotIn("secret", result)

    def test_regenerate_returns_new_secret_and_updates_hash(self):
        api_key = APIKey.objects.create(
            merchant=self.user,
            label="Primary",
            key=APIKey.generate_key(),
            secret="",
        )
        api_key.set_secret("rg_secret_old")
        api_key.save(update_fields=["secret"])

        response = self.client.post(f"/api/stores/api-keys/{api_key.id}/regenerate/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret", response.data)
        api_key.refresh_from_db()
        self.assertNotEqual(api_key.secret, response.data["secret"])
        self.assertTrue(api_key.check_secret(response.data["secret"]))


class StoreConnectionSyncViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant-sync@example.com",
            username="merchant_sync",
            first_name="Merchant",
            last_name="Sync",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)
        self.connection = StoreConnection.objects.create(
            merchant=self.user,
            platform="shopify",
            store_url="https://demo-store.myshopify.com",
            access_token="shpat_test_token",
            is_active=True,
        )

    @patch("apps.stores.views.sync_shopify_connection")
    def test_sync_returns_partial_failure_detail_message(self, sync_mock):
        sync_mock.return_value = {
            "imported": 2,
            "updated": 0,
            "failed": 1,
            "failed_orders": [{"shopify_order_id": "123", "error": "broken line item"}],
            "fetched": 3,
            "domain": "demo-store.myshopify.com",
            "requested_limit": 50,
        }

        response = self.client.post(
            f"/api/stores/connections/{self.connection.id}/sync/",
            {"limit": 50},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("finished with some failed orders", response.data["detail"])
        self.assertEqual(response.data["summary"]["failed"], 1)


class CourierCoverageCacheTests(TestCase):
    def tearDown(self):
        invalidate_coverage_cache()

    def test_admin_branch_save_invalidates_reachability_cache(self):
        self.assertFalse(check_reachability("Swabi", "Swabi, Khyber Pakhtunkhwa").is_reachable)

        CourierBranch.objects.create(
            brand="TCS Courier",
            branch_name="TCS Courier Swabi Branch",
            city_normalized="swabi",
            is_active=True,
        )

        result = check_reachability("Swabi", "Swabi, Khyber Pakhtunkhwa")

        self.assertTrue(result.is_reachable)
        self.assertEqual(result.match_confidence, "exact")
        self.assertIn("TCS Courier", result.reachable_couriers)

    def test_province_token_is_not_treated_as_courier_city_coverage(self):
        CourierBranch.objects.create(
            brand="TCS Courier",
            branch_name="TCS Courier Sindh Branch",
            city_normalized="sindh",
            is_active=True,
        )

        result = check_reachability(
            "Chaudry",
            "Bandar gali Shaitan chowk chashni, Chaudry, Sindh, Pakistan",
        )

        self.assertFalse(result.is_reachable)
        self.assertEqual(result.match_confidence, "none")

    def test_address_token_match_still_works_for_real_city_names(self):
        CourierBranch.objects.create(
            brand="TCS Courier",
            branch_name="TCS Courier Karachi Branch",
            city_normalized="karachi",
            is_active=True,
        )

        result = check_reachability(
            "Unknown Area",
            "Street 2, Saddar, Karachi, Sindh, Pakistan",
        )

        self.assertTrue(result.is_reachable)
        self.assertEqual(result.match_confidence, "city_level")


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class ShopifySyncServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant-service@example.com",
            username="merchant_service",
            first_name="Merchant",
            last_name="Service",
            password="StrongPass123!",
        )
        self.connection = StoreConnection.objects.create(
            merchant=self.user,
            platform="shopify",
            store_url="https://demo-store.myshopify.com",
            access_token="shpat_test_token",
            is_active=True,
        )

    def test_sync_rejects_non_integer_limit(self):
        with self.assertRaises(ShopifySyncError):
            sync_shopify_connection(self.connection, limit="not-a-number")

    def test_sync_rejects_limit_above_scaled_cap(self):
        with self.assertRaises(ShopifySyncError):
            sync_shopify_connection(self.connection, limit=1001)

    def test_placeholder_zip_does_not_make_address_valid(self):
        metadata = _bootstrap_address_metadata(
            {
                "address1": "str 11 block A, Phase 3 hayatabad Peshawar",
                "city": "peshawar",
                "province": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
                "zip": "-",
            },
            {
                "address1": "str 11 block A, Phase 3 hayatabad Peshawar",
                "city": "peshawar",
                "province": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
                "zip": "-",
            },
            {
                "address1": "str 11 block A, Phase 3 hayatabad Peshawar",
                "city": "peshawar",
                "province": "Khyber Pakhtunkhwa",
                "country": "Pakistan",
                "zip": "-",
            },
        )

        self.assertEqual(metadata["status"], "partial")
        # A placeholder zip keeps the address out of "valid"; confidence reflects
        # real completeness + billing agreement only (no fabricated area penalty).
        self.assertLessEqual(metadata["confidence_score"], 81.0)

    @patch("apps.stores.shopify_sync.requests.post")
    @patch("apps.stores.shopify_sync.requests.get")
    def test_sync_persists_source_snapshot_and_returns_order_ids(self, get_mock, post_mock):
        rest_response = Mock()
        rest_response.status_code = 200
        rest_response.json.return_value = {
            "orders": [
                {
                    "id": 987654321,
                    "email": "buyer@example.com",
                    "source_name": "web",
                    "source_identifier": "fb-campaign-1",
                    "browser_ip": "203.0.113.10",
                    "client_details": {
                        "browser_ip": "203.0.113.10",
                        "user_agent": "Mozilla/5.0",
                        "session_hash": "sess_123",
                    },
                    "financial_status": "paid",
                    "fulfillment_status": None,
                    "current_total_price": "4200.00",
                    "payment_gateway_names": ["Cash on Delivery (COD)"],
                    "shipping_address": {
                        "first_name": "Ali",
                        "last_name": "Khan",
                        "phone": "+923001234567",
                        "address1": "House 1",
                        "city": "Karachi",
                        "province": "Sindh",
                        "country": "Pakistan",
                        "zip": "75000",
                    },
                    "billing_address": {
                        "first_name": "Ali",
                        "last_name": "Khan",
                        "phone": "+923001234567",
                        "address1": "House 99",
                        "city": "Karachi",
                        "province": "Sindh",
                        "country": "Pakistan",
                        "zip": "75000",
                    },
                    "customer": {
                        "first_name": "Ali",
                        "last_name": "Khan",
                        "phone": "+923001234567",
                        "email": "buyer@example.com",
                        "orders_count": 4,
                    },
                    "line_items": [
                        {
                            "name": "Wireless Earbuds",
                            "quantity": 1,
                            "price": "4200.00",
                            "sku": "SKU-1",
                            "vendor": "Audio",
                        }
                    ],
                }
            ]
        }
        get_mock.return_value = rest_response

        graphql_response = Mock()
        graphql_response.raise_for_status.return_value = None
        graphql_response.json.return_value = {
            "data": {
                "order": {
                    "id": "gid://shopify/Order/987654321",
                    "legacyResourceId": "987654321",
                    "clientIp": "203.0.113.10",
                    "sourceName": "facebook_ad",
                    "sourceIdentifier": "fb-campaign-1",
                    "registeredSourceUrl": "https://example.com/landing",
                    "displayFinancialStatus": "PAID",
                    "displayFulfillmentStatus": "UNFULFILLED",
                    "billingAddressMatchesShippingAddress": False,
                    "customerJourneySummary": {
                        "ready": True,
                        "customerOrderIndex": 2,
                        "daysToConversion": 3,
                    },
                    "risk": {
                        "recommendation": "INVESTIGATE",
                        "assessments": [
                            {
                                "riskLevel": "HIGH",
                                "facts": [
                                    {
                                        "description": "High mismatch",
                                        "sentiment": "NEGATIVE",
                                    }
                                ],
                            }
                        ],
                    },
                }
            }
        }
        post_mock.return_value = graphql_response

        summary = sync_shopify_connection(self.connection, limit=10)

        self.assertEqual(summary["imported"], 1)
        order = Order.objects.select_related("source_snapshot").get()
        self.assertEqual(summary["order_ids"], [order.id])
        self.assertEqual(order.source_snapshot.client_ip, "203.0.113.10")
        self.assertEqual(order.source_snapshot.browser_ip, "203.0.113.10")
        self.assertEqual(order.source_snapshot.shopify_risk_recommendation, "INVESTIGATE")
        self.assertEqual(order.source_snapshot.shopify_risk_level, "HIGH")
        self.assertEqual(order.source_snapshot.customer_order_index, 2)
        self.assertEqual(order.address_score, 0.0)
        self.assertEqual(order.rto_probability_score, 0.0)
        self.assertEqual(order.address.status, "mismatch")
        self.assertGreater(order.address.confidence_score, 0.0)
        # Bootstrap no longer fabricates an area RTO rate — it stays unknown (0.0)
        # until the risk engine computes a real rate from order history.
        self.assertEqual(order.address.area_rto_rate, 0.0)
        self.assertFalse(order.address.is_high_risk_area)
        self.assertEqual(order.customer.total_orders, 4)

        order.status = "verified"
        order.save(update_fields=["status"])

        summary = sync_shopify_connection(self.connection, limit=10)
        order.refresh_from_db()

        self.assertEqual(summary["updated"], 1)
        self.assertEqual(order.status, "verified")

    @patch("apps.stores.shopify_sync.requests.get")
    def test_fetch_orders_follows_shopify_cursor_pagination(self, get_mock):
        from .shopify_sync import _fetch_orders

        first_response = Mock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "orders": [{"id": 1}, {"id": 2}],
        }
        first_response.links = {
            "next": {
                "url": "https://demo-store.myshopify.com/admin/api/2025-10/orders.json?page_info=abc&limit=2",
            },
        }

        second_response = Mock()
        second_response.status_code = 200
        second_response.json.return_value = {
            "orders": [{"id": 3}, {"id": 4}],
        }
        second_response.links = {}

        get_mock.side_effect = [first_response, second_response]

        orders = _fetch_orders("demo-store.myshopify.com", "token", limit=3)

        self.assertEqual([order["id"] for order in orders], [1, 2, 3])
        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual(get_mock.call_args_list[0].kwargs["params"]["limit"], 3)
        self.assertIsNone(get_mock.call_args_list[1].kwargs["params"])

    @patch("apps.stores.shopify_sync.requests.get")
    def test_sync_skips_cancelled_orders(self, get_mock):
        rest_response = Mock()
        rest_response.status_code = 200
        rest_response.json.return_value = {
            "orders": [
                {
                    "id": 10101,
                    "cancelled_at": "2025-01-10T10:11:12Z",
                }
            ],
        }
        rest_response.links = {}
        get_mock.return_value = rest_response

        summary = sync_shopify_connection(self.connection, limit=10)

        self.assertEqual(summary["imported"], 0)
        self.assertEqual(summary["updated"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(Order.objects.count(), 0)


class ShopifyWebhookHandlerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant-webhook@example.com",
            username="merchant_webhook",
            first_name="Merchant",
            last_name="Webhook",
            password="StrongPass123!",
        )
        self.connection = StoreConnection.objects.create(
            merchant=self.user,
            platform="shopify",
            store_url="https://demo-store.myshopify.com",
            access_token="shpat_test_token",
            is_active=True,
        )

    @patch("apps.stores.webhooks.enqueue_score_order")
    @patch("apps.stores.webhooks._upsert_single_order")
    def test_webhook_upsert_skips_cancelled_orders(self, upsert_mock, enqueue_mock):
        view = ShopifyWebhookView()
        payload = {"id": 20202, "cancelled_at": "2025-01-10T10:11:12Z"}

        view._handle_order_upsert(self.connection, payload)

        upsert_mock.assert_not_called()
        enqueue_mock.assert_not_called()

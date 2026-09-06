"""Manual end-to-end script: create Shopify connection and run sync.

This script is intentionally guarded behind ``if __name__ == "__main__"`` so
it is safe to import during automated test discovery.
"""

import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model

from apps.orders.models import Order
from apps.stores.models import StoreConnection
from apps.stores.shopify_sync import sync_shopify_connection


def main() -> int:
    merchant_email = os.environ.get("SHOPIFY_TEST_MERCHANT_EMAIL", "")
    store_url = os.environ.get("SHOPIFY_TEST_STORE_URL", "")
    client_id = os.environ.get("SHOPIFY_TEST_CLIENT_ID", "")
    client_secret = os.environ.get("SHOPIFY_TEST_CLIENT_SECRET", "")
    limit = int(os.environ.get("SHOPIFY_TEST_SYNC_LIMIT", "50"))

    if not all([merchant_email, store_url, client_id, client_secret]):
        print(
            "Missing required env vars: SHOPIFY_TEST_MERCHANT_EMAIL, "
            "SHOPIFY_TEST_STORE_URL, SHOPIFY_TEST_CLIENT_ID, SHOPIFY_TEST_CLIENT_SECRET"
        )
        return 1

    User = get_user_model()
    user = User.objects.filter(email=merchant_email).first()
    if not user:
        print(f"Merchant not found for email: {merchant_email}")
        return 1

    print(f"User: {user.email}")

    conn, created = StoreConnection.objects.update_or_create(
        merchant=user,
        platform="shopify",
        defaults={
            "store_url": store_url,
            "client_id": client_id,
            "client_secret": client_secret,
            "is_active": True,
        },
    )
    print(f"Connection {'created' if created else 'updated'}: id={conn.id}")

    print("\nStarting Shopify sync...")
    try:
        summary = sync_shopify_connection(conn, limit=limit)
        print("\nSync result:")
        print(f"  Imported: {summary['imported']}")
        print(f"  Updated:  {summary['updated']}")
        print(f"  Failed:   {summary['failed']}")
        if summary.get("failed_orders"):
            for failed_order in summary["failed_orders"][:5]:
                print(
                    f"  FAIL: order {failed_order['shopify_order_id']}: "
                    f"{failed_order['error']}"
                )
    except Exception as exc:  # noqa: BLE001 - manual script diagnostics
        print(f"Sync failed: {exc}")
        return 1

    orders = Order.objects.filter(merchant=user, source="shopify").order_by("-created_at")
    print(f"\nShopify orders in DB: {orders.count()}")
    for order in orders[:5]:
        customer_name = order.customer.name if order.customer else "N/A"
        print(
            f"  - {order.order_id}: {order.amount} {order.payment_method} | "
            f"risk={order.risk_score} | customer={customer_name}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Manual script: quick test of Shopify client credentials flow.

This file is import-safe and only runs when invoked directly.
"""

import os

import requests


def main() -> int:
    shop = os.environ.get("SHOPIFY_TEST_STORE_URL", "")
    client_id = os.environ.get("SHOPIFY_TEST_CLIENT_ID", "")
    client_secret = os.environ.get("SHOPIFY_TEST_CLIENT_SECRET", "")

    if not all([shop, client_id, client_secret]):
        print(
            "Missing required env vars: SHOPIFY_TEST_STORE_URL, "
            "SHOPIFY_TEST_CLIENT_ID, SHOPIFY_TEST_CLIENT_SECRET"
        )
        return 1

    url = f"https://{shop}/admin/oauth/access_token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    token_response = requests.post(url, data=data, timeout=15)
    print(f"Token exchange status: {token_response.status_code}")
    print(f"Response: {token_response.text[:500]}")

    if token_response.status_code != 200:
        return 1

    token = token_response.json().get("access_token")
    expires = token_response.json().get("expires_in")
    scopes = token_response.json().get("scope")
    token_preview = f"{token[:20]}..." if token else "<missing token>"
    print(f"\nAccess token obtained: {token_preview}")
    print(f"Scopes: {scopes}")
    print(f"Expires in: {expires}s")

    shop_url = f"https://{shop}/admin/api/2025-01/shop.json"
    headers = {"X-Shopify-Access-Token": token}
    shop_response = requests.get(shop_url, headers=headers, timeout=15)
    print(f"\nShop API status: {shop_response.status_code}")
    if shop_response.status_code == 200:
        shop_data = shop_response.json().get("shop", {})
        name = shop_data.get("name")
        domain = shop_data.get("domain")
        print(f"Shop name: {name}")
        print(f"Domain: {domain}")

    orders_url = f"https://{shop}/admin/api/2025-01/orders.json?status=any&limit=5"
    orders_response = requests.get(orders_url, headers=headers, timeout=15)
    print(f"\nOrders API status: {orders_response.status_code}")
    if orders_response.status_code == 200:
        orders = orders_response.json().get("orders", [])
        print(f"Orders found: {len(orders)}")
        for order in orders[:3]:
            number = order.get("order_number")
            price = order.get("total_price")
            currency = order.get("currency")
            status = order.get("financial_status")
            print(f"  - #{number}: {price} {currency} ({status})")
    else:
        print(f"Orders error: {orders_response.text[:300]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

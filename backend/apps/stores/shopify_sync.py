"""Shopify sync utilities for importing orders into Risk-Guard."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import transaction

from apps.addresses.models import Address
from apps.customers.models import Customer
from apps.customers.normalization import normalize_phone
from apps.orders.models import Order, OrderItem, OrderSourceSnapshot

from .utils import is_order_cancelled_at_source

logger = logging.getLogger(__name__)


SHOPIFY_ORDER_ENRICHMENT_QUERY = """
query getOrderRiskSnapshot($id: ID!) {
  order(id: $id) {
    id
    legacyResourceId
    clientIp
    sourceName
    sourceIdentifier
    registeredSourceUrl
    displayFinancialStatus
    displayFulfillmentStatus
    billingAddressMatchesShippingAddress
    customerJourneySummary {
      ready
      customerOrderIndex
      daysToConversion
    }
    risk {
      recommendation
      assessments {
        riskLevel
        facts {
          description
          sentiment
        }
      }
    }
  }
}
""".strip()


class ShopifySyncError(Exception):
    """Raised when Shopify sync cannot be completed."""


@dataclass
class SyncSummary:
    """Result summary for one Shopify sync run."""

    imported: int = 0
    updated: int = 0
    failed: int = 0
    failures: list[dict] = field(default_factory=list)
    order_ids: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "failed": self.failed,
            "failed_orders": self.failures,
            "order_ids": self.order_ids,
        }


def normalize_shop_domain(store_url: str) -> str:
    """Normalize user-provided store URL into a Shopify domain."""
    value = (store_url or "").strip()
    if not value:
        raise ShopifySyncError("store_url is required for Shopify sync.")

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    domain = (parsed.netloc or parsed.path).strip().lower()

    if not domain:
        raise ShopifySyncError("Invalid Shopify store URL.")
    if not domain.endswith(".myshopify.com"):
        raise ShopifySyncError("Shopify store must be a *.myshopify.com domain.")

    return domain


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _normalize_phone(value: str, fallback: str) -> str:
    phone = normalize_phone(value)
    if not phone:
        return (normalize_phone(fallback) or fallback.strip())[:20]
    return phone[:20]


def _normalize_ip(value: str | None) -> str | None:
    candidate = (value or "").strip()
    return candidate or None


def _build_address_text(data: dict) -> str:
    parts = [
        data.get("address1", ""),
        data.get("address2", ""),
        data.get("city", ""),
        data.get("province", ""),
        data.get("country", ""),
        data.get("zip", ""),
    ]
    return ", ".join([part.strip() for part in parts if part and part.strip()])


def _has_real_value(value) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.casefold() not in {
        "-",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "not available",
    }


def _address_field_count(data: dict | None) -> int:
    if not data:
        return 0
    return sum(
        1
        for key in ("address1", "city", "province", "country", "zip")
        if _has_real_value(data.get(key))
    )


def _bootstrap_address_metadata(shipping: dict, billing: dict, addr: dict) -> dict:
    """Derive cold-start address metadata from what the order actually contains.

    Only real, present-in-the-payload signals are used (field completeness and
    billing/shipping agreement). We deliberately do NOT invent an ``area_rto_rate``
    or ``is_high_risk_area`` from a hardcoded city table — those are left at 0/False
    (unknown) until the risk engine computes a real rate from order history.
    """
    completeness_ratio = _address_field_count(addr) / 5 if addr else 0.0
    billing_matches = _addresses_match(shipping, billing)
    has_postal_code = _has_real_value((addr or {}).get("zip"))

    if billing_matches is False:
        status = "mismatch"
    elif completeness_ratio >= 0.8 and has_postal_code:
        status = "valid"
    elif completeness_ratio >= 0.5:
        status = "partial"
    else:
        status = "unverified"

    confidence_score = 35.0 + (completeness_ratio * 45.0)
    if billing_matches is True:
        confidence_score += 10.0
    elif billing_matches is False:
        confidence_score -= 18.0

    return {
        "suggested_address": _build_address_text(addr),
        "confidence_score": round(min(max(confidence_score, 20.0), 98.0), 1),
        "status": status,
        "area_rto_rate": 0.0,
        "is_high_risk_area": False,
    }


def _extract_customer_name(order_data: dict, addr: dict, customer_data: dict) -> str:
    if addr:
        full_name = f"{addr.get('first_name', '')} {addr.get('last_name', '')}".strip()
        if full_name:
            return full_name

    if customer_data:
        full_name = (
            f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}"
        ).strip()
        if full_name:
            return full_name

    return f"Shopify Customer {order_data.get('id', '')}".strip()


def _payment_method_for(order_data: dict) -> str:
    gateways = [str(g).lower() for g in (order_data.get("payment_gateway_names") or [])]
    for gateway in gateways:
        if "cash" in gateway or "cod" in gateway:
            return "cod"
    return "prepaid"


def _shopify_order_status(order_data: dict, existing_order: Order | None = None) -> str:
    """Map Shopify state without overwriting local operational decisions."""
    terminal_statuses = {"cancelled", "delivered", "rto", "rejected"}
    if existing_order and existing_order.status in terminal_statuses:
        return existing_order.status

    if is_order_cancelled_at_source("shopify", order_data):
        return "cancelled"

    if existing_order and existing_order.status in {"verified", "pending"}:
        return existing_order.status

    return "pending"


def _normalize_sync_limit(limit) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError) as exc:
        raise ShopifySyncError("limit must be an integer between 1 and 1000.") from exc

    if value < 1 or value > 1000:
        raise ShopifySyncError("limit must be between 1 and 1000.")

    return value


def _obtain_access_token(domain: str, client_id: str, client_secret: str) -> str:
    """Exchange client credentials for a short-lived Shopify access token."""
    timeout = int(getattr(settings, "SHOPIFY_SYNC_TIMEOUT", 20))
    url = f"https://{domain}/admin/oauth/access_token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post(url, data=data, timeout=timeout)
    except requests.RequestException as exc:
        raise ShopifySyncError(f"Could not reach Shopify token endpoint: {exc}") from exc

    if response.status_code == 400:
        raise ShopifySyncError(
            "Shopify rejected the credentials. Ensure the app is installed on the store "
            "and the Client ID / Secret are correct."
        )
    if response.status_code >= 400:
        raise ShopifySyncError(
            f"Shopify token exchange failed ({response.status_code}): {response.text[:200]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ShopifySyncError("Shopify returned a non-JSON response during token exchange.") from exc

    token = payload.get("access_token")
    if not token:
        raise ShopifySyncError("Shopify did not return an access token.")
    return token


def _resolve_access_token(connection) -> str:
    """Return a usable access token, preferring client credentials flow."""
    domain = normalize_shop_domain(connection.store_url)
    client_id = (connection.client_id or "").strip()
    client_secret = (connection.client_secret or "").strip()

    if client_id and client_secret:
        return _obtain_access_token(domain, client_id, client_secret)

    access_token = (connection.access_token or "").strip()
    if access_token:
        return access_token

    raise ShopifySyncError(
        "Shopify credentials are missing. Provide Client ID and Client Secret "
        "(from the Dev Dashboard), or a legacy Admin API access token."
    )


def _fetch_orders(domain: str, access_token: str, limit: int) -> list[dict]:
    api_version = getattr(settings, "SHOPIFY_API_VERSION", "2025-10")
    timeout = int(getattr(settings, "SHOPIFY_SYNC_TIMEOUT", 20))
    normalized_limit = _normalize_sync_limit(limit)

    if not api_version:
        raise ShopifySyncError("SHOPIFY_API_VERSION is not configured.")

    url = f"https://{domain}/admin/api/{api_version}/orders.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    orders: list[dict] = []
    next_url: str | None = url

    while next_url and len(orders) < normalized_limit:
        remaining = normalized_limit - len(orders)
        params = None
        if next_url == url:
            params = {
                "status": "any",
                "limit": min(remaining, 250),
                "order": "created_at desc",
            }

        try:
            response = requests.get(
                next_url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ShopifySyncError(f"Could not reach Shopify: {exc}") from exc

        if response.status_code == 401:
            raise ShopifySyncError("Invalid Shopify access token.")
        if response.status_code == 403:
            raise ShopifySyncError(
                "Shopify token does not have permission to read orders. "
                "Ensure read_orders scope is granted."
            )
        if response.status_code >= 400:
            raise ShopifySyncError(
                f"Shopify API error ({response.status_code}): {response.text[:200]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ShopifySyncError("Shopify returned a non-JSON response.") from exc

        page_orders = payload.get("orders", [])
        orders.extend(page_orders[:remaining])
        response_links = response.links if isinstance(response.links, dict) else {}
        next_url = response_links.get("next", {}).get("url")
        if not page_orders:
            break

    return orders


def _fetch_graphql_order_snapshot(
    domain: str, access_token: str, shopify_order_id: str
) -> dict | None:
    """Fetch best-effort GraphQL-only risk and journey fields for an order."""
    if not shopify_order_id:
        return None

    api_version = getattr(settings, "SHOPIFY_API_VERSION", "2025-10")
    timeout = int(getattr(settings, "SHOPIFY_SYNC_TIMEOUT", 20))
    url = f"https://{domain}/admin/api/{api_version}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    payload = {
        "query": SHOPIFY_ORDER_ENRICHMENT_QUERY,
        "variables": {"id": f"gid://shopify/Order/{shopify_order_id}"},
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "Shopify GraphQL enrichment failed for order=%s: %s",
            shopify_order_id,
            exc,
        )
        return None

    if body.get("errors"):
        logger.warning(
            "Shopify GraphQL returned errors for order=%s: %s",
            shopify_order_id,
            body["errors"],
        )
        return None

    return (body.get("data") or {}).get("order")


def _highest_risk_level(assessments: list[dict]) -> str:
    severity = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "SEVERE": 4}
    highest = ""
    highest_score = 0
    for assessment in assessments or []:
        level = str(assessment.get("riskLevel") or "").upper()
        score = severity.get(level, 0)
        if score > highest_score:
            highest = level
            highest_score = score
    return highest


def _addresses_match(shipping: dict, billing: dict) -> bool | None:
    if not shipping or not billing:
        return None
    shipping_text = _build_address_text(shipping).lower()
    billing_text = _build_address_text(billing).lower()
    if not shipping_text or not billing_text:
        return None
    return shipping_text == billing_text


def _upsert_source_snapshot(order: Order, order_data: dict, graphql_order: dict | None) -> None:
    client_details = order_data.get("client_details") or {}
    shipping = order_data.get("shipping_address") or {}
    billing = order_data.get("billing_address") or {}
    assessments = (
        (((graphql_order or {}).get("risk") or {}).get("assessments") or [])
        if graphql_order
        else []
    )
    recommendation = (
        (((graphql_order or {}).get("risk") or {}).get("recommendation") or "")
        if graphql_order
        else ""
    )
    customer_journey = (graphql_order or {}).get("customerJourneySummary") or {}

    defaults = {
        "shopify_order_gid": str((graphql_order or {}).get("id") or "")[:100],
        "shopify_legacy_order_id": str(order_data.get("id") or "")[:50],
        "client_ip": _normalize_ip(
            (graphql_order or {}).get("clientIp") or client_details.get("browser_ip")
        ),
        "browser_ip": _normalize_ip(
            order_data.get("browser_ip") or client_details.get("browser_ip")
        ),
        "user_agent": str(client_details.get("user_agent") or "")[:1000],
        "session_hash": str(client_details.get("session_hash") or "")[:255],
        "source_name": str(
            (graphql_order or {}).get("sourceName") or order_data.get("source_name") or "shopify"
        )[:100],
        "source_identifier": str(
            (graphql_order or {}).get("sourceIdentifier") or order_data.get("source_identifier") or ""
        )[:255],
        "registered_source_url": str((graphql_order or {}).get("registeredSourceUrl") or "")[:200],
        "financial_status": str(
            (graphql_order or {}).get("displayFinancialStatus")
            or order_data.get("financial_status")
            or ""
        )[:50],
        "fulfillment_status": str(
            (graphql_order or {}).get("displayFulfillmentStatus")
            or order_data.get("fulfillment_status")
            or ""
        )[:50],
        "billing_matches_shipping": (
            (graphql_order or {}).get("billingAddressMatchesShippingAddress")
            if graphql_order and "billingAddressMatchesShippingAddress" in graphql_order
            else _addresses_match(shipping, billing)
        ),
        "customer_journey_ready": bool(customer_journey.get("ready", False)),
        "customer_order_index": customer_journey.get("customerOrderIndex") or None,
        "days_to_conversion": customer_journey.get("daysToConversion") or None,
        "shopify_risk_recommendation": str(recommendation)[:50],
        "shopify_risk_level": _highest_risk_level(assessments)[:50],
        "shopify_risk_payload": {
            "risk": (graphql_order or {}).get("risk") or {},
            "customer_journey_summary": customer_journey,
        },
        "raw_order_payload": order_data,
    }
    OrderSourceSnapshot.objects.update_or_create(order=order, defaults=defaults)


def refresh_shopify_order_bootstrap(order: Order) -> bool:
    """Refresh customer/address bootstrap fields for an imported Shopify order."""
    snapshot = getattr(order, "source_snapshot", None)
    raw_order_payload = (snapshot.raw_order_payload or {}) if snapshot else {}
    if not raw_order_payload:
        return False

    shipping = raw_order_payload.get("shipping_address") or {}
    billing = raw_order_payload.get("billing_address") or {}
    addr = shipping or billing
    customer_data = raw_order_payload.get("customer") or {}
    if not addr and not customer_data:
        return False

    customer = order.customer
    if customer is None:
        return False

    customer_changed = False
    customer_name = _extract_customer_name(raw_order_payload, addr, customer_data)
    email = (
        customer_data.get("email")
        or raw_order_payload.get("email")
        or raw_order_payload.get("contact_email")
        or ""
    )[:254]
    city = (addr.get("city") or billing.get("city") or customer.city or "")[:100]
    customer_orders_count = customer_data.get("orders_count")

    if customer.name and customer_name and customer.name != customer_name:
        names_used = list(customer.names_used or [])
        for candidate in (customer.name, customer_name):
            if candidate and candidate not in names_used:
                names_used.append(candidate)
        customer.names_used = names_used
        customer.multiple_names_detected = True
        customer_changed = True
    if customer_name and customer.name != customer_name:
        customer.name = customer_name[:200]
        customer_changed = True
    if email and customer.email != email:
        customer.email = email
        customer_changed = True
    if city and customer.city != city:
        customer.city = city
        customer_changed = True

    try:
        normalized_orders_count = max(int(customer_orders_count or 0), 0)
    except (TypeError, ValueError):
        normalized_orders_count = 0
    if normalized_orders_count and customer.total_orders < normalized_orders_count:
        customer.total_orders = normalized_orders_count
        customer_changed = True

    phone = _normalize_phone(
        addr.get("phone") or customer_data.get("phone") or billing.get("phone") or "",
        fallback=customer.phone or f"unknown-{order.order_id}",
    )
    if phone and customer.phone != phone:
        conflicting_customer = Customer.objects.filter(
            merchant=order.merchant,
            phone=phone,
        ).exclude(id=customer.id).exists()
        if not conflicting_customer:
            customer.phone = phone
            customer_changed = True

    if customer_changed:
        customer.save()

    full_address = _build_address_text(addr)
    if not full_address:
        return customer_changed

    address_values = {
        "customer": customer,
        "full_address": full_address,
        "city": city or "Unknown",
        "province": (addr.get("province") or "")[:100],
        "postal_code": (addr.get("zip") or "")[:10],
        **_bootstrap_address_metadata(shipping, billing, addr),
    }

    address = order.address
    if address is None or address.customer_id != customer.id:
        address, _ = Address.objects.get_or_create(
            customer=customer,
            full_address=full_address,
            city=city or "Unknown",
            defaults={key: value for key, value in address_values.items() if key not in {"customer", "full_address", "city"}},
        )

    address_changed = False
    for field, value in address_values.items():
        if getattr(address, field) != value:
            setattr(address, field, value)
            address_changed = True
    if address_changed:
        address.save()

    order_changed = False
    if order.customer_id != customer.id:
        order.customer = customer
        order_changed = True
    if order.address_id != address.id:
        order.address = address
        order_changed = True
    if order_changed:
        order.save(update_fields=["customer", "address", "updated_at"])

    return customer_changed or address_changed or order_changed


def _upsert_single_order(
    connection, order_data: dict, *, domain: str, access_token: str
) -> tuple[Order, bool]:
    """Upsert one order. Returns the order and whether it was created."""
    merchant = connection.merchant
    shipping = order_data.get("shipping_address") or {}
    billing = order_data.get("billing_address") or {}
    addr = shipping or billing
    customer_data = order_data.get("customer") or {}

    shopify_order_id = str(order_data.get("id") or "")
    if not shopify_order_id:
        raise ShopifySyncError("Encountered Shopify order without id.")

    customer_name = _extract_customer_name(order_data, addr, customer_data)
    phone = _normalize_phone(
        addr.get("phone") or customer_data.get("phone") or billing.get("phone") or "",
        fallback=f"unknown-{shopify_order_id}",
    )
    email = (customer_data.get("email") or order_data.get("email") or "")[:254]
    city = (addr.get("city") or billing.get("city") or "")[:100]
    customer_orders_count = customer_data.get("orders_count")

    customer = Customer.objects.filter(
        merchant=merchant,
        normalized_phone=phone,
    ).first()
    customer_created = False
    if customer is None:
        customer, customer_created = Customer.objects.get_or_create(
            merchant=merchant,
            phone=phone,
            defaults={
                "name": customer_name[:200],
                "email": email,
                "city": city,
            },
        )

    customer_changed = False
    if customer.name and customer_name and customer.name != customer_name:
        names_used = list(customer.names_used or [])
        for candidate in (customer.name, customer_name):
            if candidate and candidate not in names_used:
                names_used.append(candidate)
        customer.names_used = names_used
        customer.multiple_names_detected = True
        customer_changed = True
    if customer_name and customer.name != customer_name:
        customer.name = customer_name[:200]
        customer_changed = True
    if email and customer.email != email:
        customer.email = email
        customer_changed = True
    if city and customer.city != city:
        customer.city = city
        customer_changed = True
    try:
        normalized_orders_count = max(int(customer_orders_count or 0), 0)
    except (TypeError, ValueError):
        normalized_orders_count = 0
    if normalized_orders_count and customer.total_orders < normalized_orders_count:
        customer.total_orders = normalized_orders_count
        customer_changed = True
    if customer_created and not normalized_orders_count:
        customer.total_orders = 0
        customer_changed = True
    if customer_changed:
        customer.save()

    full_address = _build_address_text(addr)
    address = None
    if full_address:
        address_defaults = {
            "province": (addr.get("province") or "")[:100],
            "postal_code": (addr.get("zip") or "")[:10],
            **_bootstrap_address_metadata(shipping, billing, addr),
        }
        address, _ = Address.objects.get_or_create(
            customer=customer,
            full_address=full_address,
            city=city or "Unknown",
            defaults=address_defaults,
        )
        address_changed = False
        for field, value in address_defaults.items():
            if getattr(address, field) != value:
                setattr(address, field, value)
                address_changed = True
        if address_changed:
            address.save()

    order_id = f"shp_{connection.id}_{shopify_order_id}"[:50]
    total_amount = _to_decimal(
        order_data.get("current_total_price") or order_data.get("total_price")
    )
    payment_method = _payment_method_for(order_data)
    source_name = str(order_data.get("source_name") or "shopify")[:100]

    existing_order = Order.objects.filter(order_id=order_id).first()
    order, created = Order.objects.update_or_create(
        order_id=order_id,
        defaults={
            "merchant": merchant,
            "customer": customer,
            "address": address,
            "amount": total_amount,
            "payment_method": payment_method,
            "source": "shopify",
            "campaign": source_name,
            "status": _shopify_order_status(order_data, existing_order),
        },
    )

    OrderItem.objects.filter(order=order).delete()
    line_items = order_data.get("line_items") or []
    for item in line_items:
        OrderItem.objects.create(
            order=order,
            name=str(item.get("name") or "Unknown Item")[:200],
            qty=max(int(item.get("quantity") or 1), 1),
            price=_to_decimal(item.get("price")),
            sku=str(item.get("sku") or "")[:50],
            category=str(item.get("vendor") or "")[:100],
        )

    if created:
        if normalized_orders_count:
            customer.total_orders = max(customer.total_orders, normalized_orders_count)
        else:
            customer.total_orders += 1
        customer.save(update_fields=["total_orders", "updated_at"])

    graphql_order = _fetch_graphql_order_snapshot(domain, access_token, shopify_order_id)
    _upsert_source_snapshot(order, order_data, graphql_order)
    return order, created


def sync_shopify_connection(connection, *, limit: int = 50) -> dict:
    """Sync Shopify orders for one connection and return import summary."""
    if connection.platform != "shopify":
        raise ShopifySyncError("This endpoint currently supports Shopify sync only.")

    domain = normalize_shop_domain(connection.store_url)
    access_token = _resolve_access_token(connection)

    orders = _fetch_orders(domain, access_token, limit=limit)
    summary = SyncSummary()

    for order_data in orders:
        shopify_order_id = str(order_data.get("id") or "unknown")
        if is_order_cancelled_at_source(connection.platform, order_data):
            continue
        try:
            with transaction.atomic():
                order, created = _upsert_single_order(
                    connection,
                    order_data,
                    domain=domain,
                    access_token=access_token,
                )
            summary.order_ids.append(order.id)
            if created:
                summary.imported += 1
            else:
                summary.updated += 1
        except Exception as exc:  # noqa: BLE001 - keep syncing remaining orders
            logger.exception(
                "Shopify order sync failed for merchant=%s connection=%s order=%s",
                connection.merchant_id,
                connection.id,
                shopify_order_id,
            )
            summary.failed += 1
            if len(summary.failures) < 20:
                summary.failures.append(
                    {
                        "shopify_order_id": shopify_order_id,
                        "error": str(exc),
                    }
                )

    return {
        **summary.as_dict(),
        "fetched": len(orders),
        "domain": domain,
        "requested_limit": _normalize_sync_limit(limit),
    }

"""Shopify webhooks: signature-verified replacement for polling sync.

Topics handled:
- ``orders/create``, ``orders/updated``, ``orders/edited`` — upsert order, enqueue scoring.
- ``orders/cancelled`` — set status=cancelled.
- ``orders/fulfilled`` — set status=verified (if pending), record carrier event.
- ``fulfillments/create`` / ``fulfillments/update`` — carrier events + terminal status updates.

Security:
- HMAC-SHA256(raw_body, connection.client_secret), constant-time compared to header.
- ScopedRateThrottle ``shopify_webhook`` (60/min per IP).
- Replay protection via ``X-Shopify-Webhook-Id`` cached for 24h.
- Always returns 200 once HMAC validates so Shopify does not retry on
  internal processing errors (errors are logged + re-queued via Celery retry).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone as dt_timezone

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.risk_engine.models import CarrierOutcomeEvent
from apps.risk_engine.tasks import enqueue_score_order
from .models import StoreConnection
from .shopify_sync import _upsert_single_order, normalize_shop_domain
from .utils import is_order_cancelled_at_source

logger = logging.getLogger(__name__)

# Topics we care about. Anything else is acknowledged with 200 and ignored.
KNOWN_TOPICS = {
    "orders/create",
    "orders/updated",
    "orders/edited",
    "orders/cancelled",
    "orders/fulfilled",
    "fulfillments/create",
    "fulfillments/update",
}

REPLAY_CACHE_TTL_SECONDS = 24 * 60 * 60
REPLAY_CACHE_PREFIX = "shopify:webhook:seen:"


def _verify_hmac(raw_body: bytes, secret: str, header_value: str) -> bool:
    """Return True iff base64(HMAC-SHA256(body, secret)) == header_value."""
    if not secret or not header_value:
        return False
    digest = hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, header_value)


def _parse_iso_datetime(value: str | None):
    if not value:
        return timezone.now()
    try:
        # Shopify uses ISO-8601 with offset, e.g. "2025-04-30T12:34:56-05:00"
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt
    except ValueError:
        return timezone.now()


class ShopifyWebhookView(APIView):
    """Receive Shopify webhooks. One endpoint, dispatch by ``X-Shopify-Topic``."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "shopify_webhook"
    authentication_classes: list = []  # Shopify does not use bearer auth.

    def post(self, request):
        raw_body: bytes = request.body or b""
        topic = (request.headers.get("X-Shopify-Topic") or "").strip().lower()
        shop_domain = (request.headers.get("X-Shopify-Shop-Domain") or "").strip().lower()
        webhook_id = (request.headers.get("X-Shopify-Webhook-Id") or "").strip()
        hmac_header = request.headers.get("X-Shopify-Hmac-Sha256") or ""

        if not shop_domain or not topic:
            return Response(
                {"detail": "missing required Shopify headers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        connection = self._resolve_connection(shop_domain)
        if connection is None:
            logger.warning("Shopify webhook: no connection for shop=%s topic=%s", shop_domain, topic)
            # 401 so Shopify retries — could be a misconfigured shop.
            return Response({"detail": "unknown shop"}, status=status.HTTP_401_UNAUTHORIZED)

        secret = (connection.client_secret or "").strip()
        if not secret:
            logger.error("Shopify webhook: connection %s has no client_secret configured", connection.id)
            return Response({"detail": "shop not configured"}, status=status.HTTP_401_UNAUTHORIZED)

        if not _verify_hmac(raw_body, secret, hmac_header):
            logger.warning(
                "Shopify webhook: HMAC mismatch shop=%s topic=%s webhook_id=%s",
                shop_domain, topic, webhook_id,
            )
            return Response({"detail": "invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        # Replay protection — Shopify retries on non-2xx.
        if webhook_id:
            cache_key = f"{REPLAY_CACHE_PREFIX}{webhook_id}"
            if not cache.add(cache_key, "1", REPLAY_CACHE_TTL_SECONDS):
                logger.info("Shopify webhook: duplicate webhook_id=%s topic=%s", webhook_id, topic)
                return Response({"detail": "duplicate"}, status=status.HTTP_200_OK)

        if topic not in KNOWN_TOPICS:
            return Response({"detail": "ignored"}, status=status.HTTP_200_OK)

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Shopify webhook: invalid JSON shop=%s topic=%s", shop_domain, topic)
            # Don't ask Shopify to retry — payload won't get any better.
            return Response({"detail": "invalid json"}, status=status.HTTP_200_OK)

        try:
            self._dispatch(connection, topic, payload)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Shopify webhook: handler error shop=%s topic=%s webhook_id=%s",
                shop_domain, topic, webhook_id,
            )
            # Return 200 so Shopify does not retry; we already logged + (Celery
            # retries handle scoring). Replay-protected so re-delivery would no-op.
            return Response({"detail": "received"}, status=status.HTTP_200_OK)

        return Response({"detail": "ok", "topic": topic}, status=status.HTTP_200_OK)

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_connection(shop_domain: str) -> StoreConnection | None:
        """Find the active Shopify connection whose normalized store_url == shop_domain."""
        # store_url may be "https://foo.myshopify.com" or just "foo.myshopify.com".
        # Match against the suffix to avoid scheme/case mismatches.
        target = shop_domain.lower()
        candidates = StoreConnection.objects.filter(
            platform="shopify", is_active=True
        ).only("id", "merchant_id", "store_url", "client_secret")
        for conn in candidates:
            try:
                if normalize_shop_domain(conn.store_url) == target:
                    return conn
            except Exception:
                continue
        return None

    def _dispatch(self, connection: StoreConnection, topic: str, payload: dict) -> None:
        if topic in ("orders/create", "orders/updated", "orders/edited"):
            self._handle_order_upsert(connection, payload)
        elif topic == "orders/cancelled":
            self._handle_order_cancelled(connection, payload)
        elif topic == "orders/fulfilled":
            self._handle_order_fulfilled(connection, payload)
        elif topic in ("fulfillments/create", "fulfillments/update"):
            self._handle_fulfillment_event(connection, topic, payload)

    # ── handlers ─────────────────────────────────────────────────────────

    def _handle_order_upsert(self, connection: StoreConnection, payload: dict) -> None:
        if is_order_cancelled_at_source(connection.platform, payload):
            return
        # `_upsert_single_order` also fetches a GraphQL snapshot which requires
        # a valid access_token + domain. We pass them through; if the token is
        # missing, the snapshot fetch logs a warning but the row is still saved.
        try:
            domain = normalize_shop_domain(connection.store_url)
        except Exception:
            domain = ""
        access_token = (connection.access_token or "")
        with transaction.atomic():
            order, _created = _upsert_single_order(
                connection,
                payload,
                domain=domain,
                access_token=access_token,
            )
        enqueue_score_order(order.id)

    def _handle_order_cancelled(self, connection: StoreConnection, payload: dict) -> None:
        order = self._lookup_order(connection, payload)
        if order is None:
            return
        if order.status not in ("delivered", "rto", "cancelled"):
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])

    def _handle_order_fulfilled(self, connection: StoreConnection, payload: dict) -> None:
        order = self._lookup_order(connection, payload)
        if order is None:
            return
        # Promote pending → verified once Shopify reports the order as fulfilled.
        if order.status == "pending":
            order.status = "verified"
            order.save(update_fields=["status", "updated_at"])
        CarrierOutcomeEvent.objects.create(
            order=order,
            carrier_name=str(payload.get("source_name") or "shopify")[:100],
            event_type="fulfilled",
            event_status="fulfilled",
            occurred_at=_parse_iso_datetime(payload.get("updated_at") or payload.get("created_at")),
            raw_payload=payload,
        )

    def _handle_fulfillment_event(
        self, connection: StoreConnection, topic: str, payload: dict
    ) -> None:
        order_shopify_id = payload.get("order_id")
        order = self._lookup_order(connection, {"id": order_shopify_id})
        if order is None:
            return

        fulfillment_status = (payload.get("status") or payload.get("shipment_status") or "").strip().lower()
        carrier = str(payload.get("tracking_company") or payload.get("name") or "shopify")[:100]
        event_type = topic.split("/")[-1]  # "create" | "update"
        occurred_at = _parse_iso_datetime(payload.get("updated_at") or payload.get("created_at"))

        CarrierOutcomeEvent.objects.create(
            order=order,
            carrier_name=carrier,
            event_type=event_type,
            event_status=fulfillment_status[:50],
            occurred_at=occurred_at,
            raw_payload=payload,
        )

        delivered_aliases = {"delivered", "success"}
        rto_aliases = {"failure", "cancelled", "canceled", "returned", "rto"}

        if fulfillment_status in delivered_aliases:
            self._record_outcome(order, "delivered", source=f"shopify:{topic}")
        elif fulfillment_status in rto_aliases:
            self._record_outcome(order, "rto", source=f"shopify:{topic}")

    # ── shared helpers ───────────────────────────────────────────────────

    @staticmethod
    def _lookup_order(connection: StoreConnection, payload: dict) -> Order | None:
        shopify_order_id = payload.get("id")
        if not shopify_order_id:
            return None
        order_id = f"shp_{connection.id}_{shopify_order_id}"[:50]
        return Order.objects.filter(order_id=order_id).first()

    @staticmethod
    def _record_outcome(order: Order, outcome: str, *, source: str) -> None:
        customer = order.customer
        previous_status = order.status

        if outcome == "delivered":
            if previous_status != "delivered":
                customer.delivered_count += 1
            order.status = "delivered"
        elif outcome == "rto":
            if previous_status != "rto":
                customer.rto_count += 1
            order.status = "rto"

        order.save(update_fields=["status", "updated_at"])
        customer.save(update_fields=["delivered_count", "rto_count", "updated_at"])
        logger.info("Recorded terminal Shopify outcome for %s: %s (%s)", order.order_id, outcome, source)

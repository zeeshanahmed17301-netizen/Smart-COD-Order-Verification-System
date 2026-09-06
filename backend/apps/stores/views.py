"""Store views."""
import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import StoreConnection, APIKey, Webhook

logger = logging.getLogger(__name__)
from .serializers import (
    StoreConnectionSerializer,
    APIKeySerializer,
    APIKeyCredentialSerializer,
    WebhookSerializer,
)
from .shopify_sync import sync_shopify_connection, ShopifySyncError


class StoreConnectionViewSet(viewsets.ModelViewSet):
    """Manage store platform connections."""

    serializer_class = StoreConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StoreConnection.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        """Trigger a manual sync with the store platform."""
        connection = self.get_object()
        limit = request.data.get("limit", 50)
        try:
            summary = sync_shopify_connection(connection, limit=limit)
        except ShopifySyncError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        connection.last_sync_at = timezone.now()
        connection.is_active = True
        connection.save(update_fields=["last_sync_at", "is_active", "updated_at"])

        # Auto-run fraud + RTO detection on every imported/updated order. Bringing
        # an order onto the platform must immediately produce a risk decision —
        # the bulk sync path previously left orders unscored (only the realtime
        # webhook scored them). Done synchronously so it works without Celery.
        scored = self._score_synced_orders(summary.get("order_ids") or [])
        summary["scored"] = scored

        had_failures = bool(summary.get("failed"))
        detail_message = (
            "Shopify sync finished with some failed orders. "
            "Check summary.failed_orders for details."
            if had_failures
            else "Shopify sync completed successfully."
        )

        return Response(
            {
                "detail": detail_message,
                "summary": summary,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _score_synced_orders(order_ids: list[int]) -> int:
        """Score each freshly-synced order. Returns the count successfully scored."""
        if not order_ids:
            return 0
        from apps.orders.models import Order
        from apps.risk_engine.services import RiskScoringEngine

        orders = (
            Order.objects.filter(id__in=order_ids)
            .select_related("customer", "address", "source_snapshot", "enrichment")
            .prefetch_related("items")
        )
        scored = 0
        for order in orders:
            try:
                RiskScoringEngine.score_and_save(order)
                scored += 1
            except Exception:
                logger.exception("Post-sync scoring failed for order %s", order.order_id)
        return scored


class APIKeyViewSet(viewsets.ModelViewSet):
    """Manage API keys for external integrations."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in {"create", "regenerate"}:
            return APIKeyCredentialSerializer
        return APIKeySerializer

    def get_queryset(self):
        return APIKey.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        raw_secret = APIKey.generate_secret()
        instance = serializer.save(
            merchant=self.request.user,
            key=APIKey.generate_key(),
            secret="",
        )
        instance.set_secret(raw_secret)
        instance.save(update_fields=["secret"])
        self._last_created_api_secret = raw_secret

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["secret"] = getattr(self, "_last_created_api_secret", None)
        return response

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk=None):
        """Regenerate API key and secret."""
        api_key = self.get_object()
        api_key.key = APIKey.generate_key()
        raw_secret = APIKey.generate_secret()
        api_key.set_secret(raw_secret)
        api_key.save(update_fields=["key", "secret"])
        payload = APIKeyCredentialSerializer(api_key).data
        payload["secret"] = raw_secret
        return Response(payload)


class WebhookViewSet(viewsets.ModelViewSet):
    """Manage webhook endpoints."""

    serializer_class = WebhookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Webhook.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user)

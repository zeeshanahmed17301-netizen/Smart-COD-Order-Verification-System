"""Views for orders — CRUD with accept/confirm/cancel actions."""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.risk_engine.services import RiskScoringEngine
from .models import Order
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
)
from .filters import OrderFilterSet


class OrderViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for COD orders scoped to the authenticated merchant.

    List uses flat OrderListSerializer.
    Retrieve uses nested OrderDetailSerializer.
    Create uses OrderCreateSerializer with nested items.
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilterSet
    search_fields = [
        "order_id",
        "customer__name",
        "customer__phone",
        "customer__email",
        "address__city",
        "source_snapshot__source_name",
        "source_snapshot__raw_order_payload__contact_email",
        "source_snapshot__raw_order_payload__phone",
        "source_snapshot__raw_order_payload__customer__phone",
        "source_snapshot__raw_order_payload__shipping_address__phone",
        "source_snapshot__raw_order_payload__shipping_address__city",
        "source_snapshot__raw_order_payload__shipping_address__first_name",
        "source_snapshot__raw_order_payload__shipping_address__last_name",
        "source_snapshot__raw_order_payload__customer__first_name",
        "source_snapshot__raw_order_payload__customer__last_name",
    ]
    ordering_fields = ["created_at", "risk_score", "amount", "fraud_score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Order.objects
            .filter(merchant=self.request.user)
            .select_related(
                "customer",
                "address",
                "conversation",
                "whatsapp_interaction",
                "source_snapshot",
                "enrichment",
            )
            .prefetch_related("items", "risk_factors", "conversation__messages")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return OrderCreateSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        order = serializer.save(merchant=self.request.user)
        order.customer.total_orders += 1
        order.customer.save(update_fields=["total_orders", "updated_at"])
        RiskScoringEngine.score_and_save(order)

    def perform_update(self, serializer):
        order = serializer.save()
        RiskScoringEngine.score_and_save(order)

    def _ensure_pending(self, order, action_name: str):
        if order.status not in ("pending",):
            return Response(
                {"detail": f"Only pending orders can be {action_name}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def _serialize_order(self, order):
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)

    def _send_admin_confirmation_message(self, order):
        from apps.chatbot.services import ConversationService

        ConversationService.send_admin_confirmation_message(order)

    def _send_admin_cancellation_message(self, order):
        from apps.chatbot.services import ConversationService

        ConversationService.send_admin_cancellation_message(order)

    def _accept_order(self, order):
        pending_error = self._ensure_pending(order, "accepted")
        if pending_error:
            return pending_error
        order.status = "verified"
        order.save(update_fields=["status", "updated_at"])
        return self._serialize_order(order)

    def _confirm_order(self, order):
        pending_error = self._ensure_pending(order, "confirmed")
        if pending_error:
            return pending_error
        order.status = "verified"
        order.save(update_fields=["status", "updated_at"])
        self._send_admin_confirmation_message(order)
        return self._serialize_order(order)

    def _cancel_order(self, order):
        pending_error = self._ensure_pending(order, "cancelled")
        if pending_error:
            return pending_error
        order.status = "cancelled"
        order.chat_status = "denied"
        order.save(update_fields=["status", "chat_status", "updated_at"])
        # Accumulate the cancellation onto the customer's history so the pattern
        # feeds future fraud/RTO scoring (cancelled_count is a scored signal).
        order.customer.cancelled_count += 1
        order.customer.save(update_fields=["cancelled_count", "updated_at"])
        self._send_admin_cancellation_message(order)
        return self._serialize_order(order)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        """Accept an order without sending WhatsApp."""
        order = self.get_object()
        return self._accept_order(order)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        """Confirm an order and send the admin confirmation WhatsApp."""
        order = self.get_object()
        return self._confirm_order(order)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel an order and send the cancellation WhatsApp."""
        order = self.get_object()
        return self._cancel_order(order)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Legacy alias for accept."""
        order = self.get_object()
        return self._accept_order(order)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Legacy alias for cancel."""
        order = self.get_object()
        return self._cancel_order(order)

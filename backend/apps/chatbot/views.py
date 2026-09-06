"""Chatbot views."""
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from .models import ChatbotSettings, Conversation, Message
from .serializers import (
    ChatbotSettingsSerializer,
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
)
from .twilio_service import TwilioService


class ChatbotSettingsView(generics.RetrieveUpdateAPIView):
    """Get or update merchant's chatbot/WhatsApp settings."""

    serializer_class = ChatbotSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> ChatbotSettings:
        settings, _ = ChatbotSettings.objects.get_or_create(
            merchant=self.request.user
        )
        return settings


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """List and view conversations — messaging logs."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Conversation.objects
            .filter(order__merchant=self.request.user)
            .select_related("order", "order__customer")
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationListSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """CRUD for messages within a conversation."""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get("conversation_pk")
        return Message.objects.filter(
            conversation_id=conversation_id,
            conversation__order__merchant=self.request.user,
        )

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get("conversation_pk")
        serializer.save(conversation_id=conversation_id)


class TriggerWhatsAppView(APIView):
    """Manually trigger a WhatsApp verification message for an order.

    Deletes any previous failed/cancelled conversation so a fresh one is created.
    Endpoint: POST /api/chatbot/trigger/
    Body: { "order_id": <int> }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"detail": "order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = (
                Order.objects
                .select_related("merchant", "customer", "address", "enrichment")
                .prefetch_related("items")
                .get(id=order_id, merchant=request.user)
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if not TwilioService.is_configured():
            return Response(
                {"detail": "WhatsApp sender is not configured. Add Twilio credentials in settings."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Remove any failed/cancelled conversation so a fresh one can be created
        Conversation.objects.filter(
            order=order,
            status__in=("failed", "cancelled"),
        ).delete()

        # Block re-trigger for active/awaiting/completed conversations
        existing = Conversation.objects.filter(order=order).first()
        if existing:
            return Response(
                {
                    "detail": f"Conversation already active (status: {existing.status}). Cannot re-trigger.",
                    "status": existing.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        from .services import ConversationService
        conversation = ConversationService.start_conversation(order, purpose="address_verification")

        if conversation is None:
            return Response(
                {"detail": "Could not start conversation. Check customer phone number."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            {
                "detail": "WhatsApp message sent.",
                "conversation_id": conversation.id,
                "status": conversation.status,
            },
            status=status.HTTP_201_CREATED,
        )

"""Chatbot serializers."""
from rest_framework import serializers
from .models import ChatbotSettings, Conversation, Message, WhatsAppInteraction
from .twilio_service import TwilioService


class ChatbotSettingsSerializer(serializers.ModelSerializer):
    is_connected = serializers.SerializerMethodField()
    platform_is_configured = serializers.SerializerMethodField()
    platform_whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = ChatbotSettings
        fields = [
            "id", "whatsapp_number", "api_key", "is_connected",
            "platform_is_configured", "platform_whatsapp_number",
            "auto_send_confirmation", "confirmation_delay_minutes",
            "auto_cancel_timeout_minutes", "language",
            "greeting_template", "confirmation_template",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "api_key": {"write_only": True},
        }

    @staticmethod
    def get_is_connected(obj: ChatbotSettings) -> bool:
        return TwilioService.is_configured()

    @staticmethod
    def get_platform_is_configured(obj: ChatbotSettings) -> bool:
        return TwilioService.is_configured()

    @staticmethod
    def get_platform_whatsapp_number(obj: ChatbotSettings) -> str:
        return TwilioService.platform_sender_number()

    def update(self, instance: ChatbotSettings, validated_data: dict) -> ChatbotSettings:
        validated_data.pop("whatsapp_number", None)
        validated_data.pop("api_key", None)
        return super().update(instance, validated_data)


class MessageSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "sender", "content", "message_sid", "parsed_data",
            "llm_model", "timestamp", "time",
        ]
        read_only_fields = ["id", "timestamp", "message_sid", "parsed_data", "llm_model"]

    def get_time(self, obj: Message) -> str:
        return obj.timestamp.strftime("%H:%M")


class ConversationListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source="order.order_id", read_only=True)
    customer_name = serializers.CharField(
        source="order.customer.name", read_only=True
    )
    message_count = serializers.IntegerField(
        source="messages.count", read_only=True
    )

    class Meta:
        model = Conversation
        fields = [
            "id", "order_id", "customer_name", "status", "purpose",
            "turn_count", "started_at", "completed_at", "message_count",
        ]


class ConversationDetailSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source="order.order_id", read_only=True)
    customer_name = serializers.CharField(
        source="order.customer.name", read_only=True
    )
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id", "order_id", "customer_name", "status", "purpose",
            "collected_data", "missing_fields", "turn_count",
            "last_message_at", "started_at", "completed_at", "messages",
        ]


class WhatsAppInteractionSerializer(serializers.ModelSerializer):
    """WhatsApp interaction summary for order detail page."""

    class Meta:
        model = WhatsAppInteraction
        fields = [
            "last_message_sent", "customer_response",
            "time_to_first_reply", "address_clarification", "nudges_sent",
        ]

"""Chatbot & messaging models."""
from django.conf import settings
from django.db import models


class ChatbotSettings(models.Model):
    """Per-merchant WhatsApp chatbot configuration."""

    merchant = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatbot_settings",
    )
    whatsapp_number = models.CharField(max_length=20, blank=True)
    api_key = models.CharField(max_length=500, blank=True)
    is_connected = models.BooleanField(default=False)

    # ── Chat flow settings ──────────────────────────────────────────────
    auto_send_confirmation = models.BooleanField(default=True)
    confirmation_delay_minutes = models.PositiveIntegerField(default=0)
    auto_cancel_timeout_minutes = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=20, default="urdu")
    greeting_template = models.TextField(
        default=(
            "📦 *Order Summary*\n\n"
            "📦 Items: {items}\n"
            "💰 Total: {amount}\n"
            "👤 Name: {customer_name}\n"
            "📍 Address: {current_address}\n"
            "🗒️ Order: #{order_id}\n\n"
            "🚀 We will ship once you confirm!\n\n"
            "Reply with:\n"
            "✅ *1* - Confirm Order\n"
            "📞 *2* - Cancel"
        )
    )
    confirmation_template = models.TextField(
        default="Your order has been confirmed. Thank you!"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "chatbot settings"

    def __str__(self) -> str:
        return f"Chatbot settings for {self.merchant.email}"


class Conversation(models.Model):
    """WhatsApp conversation linked to a specific order."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("awaiting_reply", "Awaiting Reply"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("timeout", "Timeout"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    PURPOSE_CHOICES = [
        ("address_verification", "Address Verification"),
        ("order_confirmation", "Order Confirmation"),
        ("general", "General"),
    ]

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="conversation",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active"
    )
    purpose = models.CharField(
        max_length=30, choices=PURPOSE_CHOICES, default="general"
    )
    collected_data = models.JSONField(default=dict, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    step = models.PositiveSmallIntegerField(default=1)  # 1: Confirm, 2: Landmark, 3: Human fallback, 4: Done
    turn_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Conversation for {self.order.order_id}"


class Message(models.Model):
    """Individual message in a conversation."""

    SENDER_CHOICES = [
        ("bot", "Bot"),
        ("user", "User"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    message_sid = models.CharField(max_length=50, blank=True)
    parsed_data = models.JSONField(default=dict, blank=True)
    llm_model = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"[{self.sender}] {self.content[:50]}"


class WhatsAppInteraction(models.Model):
    """Summary of WhatsApp interaction for an order (for quick display)."""

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="whatsapp_interaction",
    )
    last_message_sent = models.DateTimeField(null=True, blank=True)
    customer_response = models.CharField(max_length=200, blank=True)
    time_to_first_reply = models.CharField(max_length=50, blank=True)
    address_clarification = models.CharField(max_length=200, default="N/A")
    nudges_sent = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"WA interaction for {self.order.order_id}"

"""Store connection, API key, and webhook models."""
import secrets
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.db import models


class StoreConnection(models.Model):
    """E-commerce platform connection."""

    PLATFORM_CHOICES = [
        ("shopify", "Shopify"),
        ("daraz", "Daraz"),
        ("custom", "Custom API"),
    ]

    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_connections",
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    store_url = models.URLField(blank=True)
    access_token = models.CharField(max_length=500, blank=True)
    client_id = models.CharField(max_length=200, blank=True)
    client_secret = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["merchant", "platform"]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_platform_display()} ({self.merchant.email})"


class APIKey(models.Model):
    """API credentials for external integrations."""

    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    key = models.CharField(max_length=100, unique=True, db_index=True)
    secret = models.CharField(max_length=100)
    label = models.CharField(max_length=100, default="Default")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self) -> str:
        return f"{self.label} ({self.key[:12]}...)"

    @staticmethod
    def generate_key() -> str:
        return f"rg_live_{secrets.token_urlsafe(24)}"

    @staticmethod
    def generate_secret() -> str:
        return f"rg_secret_{secrets.token_urlsafe(24)}"

    def set_secret(self, raw_secret: str) -> None:
        """Hash API secrets so they are not stored in plaintext."""
        self.secret = make_password(raw_secret)

    def check_secret(self, raw_secret: str) -> bool:
        return check_password(raw_secret, self.secret)


class Webhook(models.Model):
    """Webhook endpoint for event notifications."""

    EVENT_CHOICES = [
        ("order.verified", "Order Verified"),
        ("order.rejected", "Order Rejected"),
        ("order.timeout", "Order Timeout"),
        ("order.delivered", "Order Delivered"),
        ("order.rto", "Order RTO"),
    ]

    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webhooks",
    )
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    url = models.URLField()
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=100, blank=True)
    delivery_count = models.PositiveIntegerField(default=0)
    last_delivery_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event} → {self.url}"

    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

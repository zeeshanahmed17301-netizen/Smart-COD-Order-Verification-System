"""Telemetry models for sessions, devices, and browser events."""
from django.conf import settings
from django.db import models


class RiskSession(models.Model):
    """Browser or app session linked to risk-relevant events."""

    session_id = models.CharField(max_length=128, unique=True)
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_sessions",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_sessions",
    )
    device_fingerprint_id = models.CharField(max_length=128, blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accept_language = models.CharField(max_length=255, blank=True)
    timezone_name = models.CharField(max_length=64, blank=True)
    landing_page_url = models.URLField(blank=True)
    referrer_url = models.URLField(blank=True)
    utm_payload = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at", "-started_at"]
        indexes = [
            models.Index(fields=["merchant", "started_at"], name="riskses_merchant_idx"),
            models.Index(fields=["device_fingerprint_id", "last_seen_at"], name="riskses_device_idx"),
            models.Index(fields=["client_ip", "last_seen_at"], name="riskses_ip_seen_idx"),
        ]

    def __str__(self) -> str:
        return self.session_id


class RiskTelemetryEvent(models.Model):
    """Event stream used to derive behavioral and velocity features."""

    session = models.ForeignKey(
        RiskSession,
        on_delete=models.CASCADE,
        related_name="events",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telemetry_events",
    )
    event_type = models.CharField(max_length=50)
    event_payload = models.JSONField(default=dict)
    schema_version = models.CharField(max_length=32)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["session", "occurred_at"], name="rtevent_session_idx"),
            models.Index(fields=["order", "occurred_at"], name="rtevent_order_idx"),
            models.Index(fields=["event_type", "occurred_at"], name="rtevent_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.session.session_id} {self.event_type}"

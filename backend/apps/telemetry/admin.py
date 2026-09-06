"""Admin registrations for telemetry models."""
from django.contrib import admin

from .models import RiskSession, RiskTelemetryEvent


@admin.register(RiskSession)
class RiskSessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_id",
        "merchant",
        "customer",
        "device_fingerprint_id",
        "client_ip",
        "started_at",
        "last_seen_at",
    ]
    list_filter = ["merchant"]
    search_fields = ["session_id", "device_fingerprint_id", "client_ip"]


@admin.register(RiskTelemetryEvent)
class RiskTelemetryEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_type",
        "session",
        "order",
        "schema_version",
        "occurred_at",
    ]
    list_filter = ["event_type", "schema_version"]
    search_fields = ["session__session_id", "order__order_id"]

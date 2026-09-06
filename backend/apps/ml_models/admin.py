"""Admin registrations for ML support models."""
from django.contrib import admin

from .models import FeatureAggregateWindow, FeatureSchemaVersion


@admin.register(FeatureSchemaVersion)
class FeatureSchemaVersionAdmin(admin.ModelAdmin):
    list_display = ["version", "target", "is_active", "created_at", "updated_at"]
    list_filter = ["target", "is_active"]
    search_fields = ["version"]


@admin.register(FeatureAggregateWindow)
class FeatureAggregateWindowAdmin(admin.ModelAdmin):
    list_display = ["entity_type", "entity_key", "window_name", "computed_at"]
    list_filter = ["entity_type", "window_name"]
    search_fields = ["entity_key"]

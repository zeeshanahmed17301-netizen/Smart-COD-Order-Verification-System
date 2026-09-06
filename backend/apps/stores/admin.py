"""Admin for stores."""
from django.contrib import admin
from .models import StoreConnection, APIKey, Webhook


@admin.register(StoreConnection)
class StoreConnectionAdmin(admin.ModelAdmin):
    list_display = ["platform", "merchant", "is_active", "last_sync_at"]
    list_filter = ["platform", "is_active"]


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ["label", "merchant", "key", "is_active", "created_at"]
    list_filter = ["is_active"]


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ["event", "url", "is_active", "delivery_count", "merchant"]
    list_filter = ["event", "is_active"]

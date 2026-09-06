"""Admin registration for orders."""
from django.contrib import admin
from .models import (
    Order,
    OrderEnrichment,
    OrderFeatureSnapshot,
    OrderItem,
    OrderSourceSnapshot,
    RiskFactor,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class RiskFactorInline(admin.TabularInline):
    model = RiskFactor
    extra = 0


class OrderSourceSnapshotInline(admin.StackedInline):
    model = OrderSourceSnapshot
    extra = 0
    can_delete = False
    readonly_fields = ["imported_at", "updated_at"]


class OrderEnrichmentInline(admin.StackedInline):
    model = OrderEnrichment
    extra = 0
    can_delete = False
    readonly_fields = ["enriched_at", "created_at", "updated_at"]


class OrderFeatureSnapshotInline(admin.TabularInline):
    model = OrderFeatureSnapshot
    extra = 0
    can_delete = False
    readonly_fields = [
        "feature_schema_version",
        "snapshot_type",
        "generated_by",
        "feature_hash",
        "generated_at",
    ]
    fields = [
        "feature_schema_version",
        "snapshot_type",
        "generated_by",
        "feature_hash",
        "generated_at",
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_id", "customer", "amount", "status",
        "risk_score", "risk_level", "score_source", "chat_status", "created_at",
    ]
    list_filter = ["status", "risk_level", "score_source", "chat_status"]
    search_fields = ["order_id", "customer__name", "customer__phone"]
    inlines = [
        OrderSourceSnapshotInline,
        OrderEnrichmentInline,
        OrderFeatureSnapshotInline,
        OrderItemInline,
        RiskFactorInline,
    ]
    readonly_fields = ["created_at", "updated_at", "rescored_at"]

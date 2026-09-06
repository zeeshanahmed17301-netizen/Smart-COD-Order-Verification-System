"""Admin for risk engine."""

from django.contrib import admin

from .models import (
    CarrierOutcomeEvent,
    MerchantRiskPolicy,
    RiskCalibrationModel,
    RiskDecisionRecord,
    RiskMLModel,
)


@admin.register(CarrierOutcomeEvent)
class CarrierOutcomeEventAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "carrier_name",
        "event_type",
        "event_status",
        "attempt_number",
        "occurred_at",
    ]
    list_filter = ["carrier_name", "event_type"]
    search_fields = ["order__order_id", "carrier_name", "event_reason_code"]


@admin.register(MerchantRiskPolicy)
class MerchantRiskPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "merchant",
        "version",
        "fraud_high_threshold",
        "rto_high_threshold",
        "auto_cancel_blacklisted",
        "updated_at",
    ]
    search_fields = ["merchant__email"]


@admin.register(RiskCalibrationModel)
class RiskCalibrationModelAdmin(admin.ModelAdmin):
    list_display = ["target", "version", "is_active", "sample_size", "auc", "ece", "trained_at"]
    list_filter = ["target", "is_active", "method"]
    readonly_fields = ["bins", "trained_at"]


@admin.register(RiskDecisionRecord)
class RiskDecisionRecordAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "recommended_action",
        "risk_level",
        "fraud_score",
        "rto_probability_score",
        "decision_policy_version",
        "created_at",
    ]
    list_filter = ["risk_level", "recommended_action", "decision_policy_version"]
    search_fields = ["order__order_id"]
    readonly_fields = [field.name for field in RiskDecisionRecord._meta.fields]


@admin.register(RiskMLModel)
class RiskMLModelAdmin(admin.ModelAdmin):
    list_display = [
        "target",
        "version",
        "role",
        "is_active",
        "holdout_auc",
        "baseline_auc",
        "train_size",
        "trained_at",
    ]
    list_filter = ["target", "role", "is_active", "algorithm"]
    readonly_fields = ["params", "trained_at"]
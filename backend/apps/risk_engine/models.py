"""Risk engine persistence models."""

from django.conf import settings
from django.db import models


class CarrierOutcomeEvent(models.Model):
    """Carrier lifecycle events retained for logistics and audit visibility."""

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="carrier_events",
    )
    carrier_name = models.CharField(max_length=100)
    event_type = models.CharField(max_length=50)
    event_status = models.CharField(max_length=50, blank=True)
    event_reason_code = models.CharField(max_length=64, blank=True)
    event_note = models.TextField(blank=True)
    attempt_number = models.PositiveIntegerField(default=0)
    occurred_at = models.DateTimeField()
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["order", "occurred_at"], name="carrier_evt_order_idx"),
            models.Index(fields=["carrier_name", "event_type", "occurred_at"], name="carrier_evt_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order.order_id} {self.carrier_name} {self.event_type}"


class RiskCalibrationModel(models.Model):
    """A fitted, versioned score→probability calibration backed by real outcomes.

    Each row is an isotonic mapping (list of ``{score_lo, score_hi, probability,
    count, positives}`` bins) fitted on historical (score, outcome) pairs for one
    target. Exactly one row per target is ``is_active``; the scorer serves it.
    This replaces the old hardcoded "probability == score" calibration shim.
    """

    TARGET_CHOICES = [
        ("fraud", "Fraud"),
        ("rto", "RTO"),
    ]

    target = models.CharField(max_length=20, choices=TARGET_CHOICES, db_index=True)
    version = models.CharField(max_length=64)
    method = models.CharField(max_length=32, default="isotonic")
    bins = models.JSONField(default=list)
    sample_size = models.PositiveIntegerField(default=0)
    positives = models.PositiveIntegerField(default=0)
    auc = models.FloatField(null=True, blank=True)
    ece = models.FloatField(null=True, blank=True)
    label_definition = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-trained_at"]
        indexes = [
            models.Index(fields=["target", "is_active"], name="riskcalib_active_idx"),
        ]

    def __str__(self) -> str:
        state = "active" if self.is_active else "inactive"
        return f"{self.target} calibration {self.version} ({state})"


class MerchantRiskPolicy(models.Model):
    """Per-merchant decision thresholds — governance over the engine's actions.

    Defaults reproduce the engine's previous hardcoded constants exactly, so an
    unconfigured merchant scores identically. A merchant whose RTO is expensive
    can lower the thresholds to cancel/verify more aggressively; one optimising
    for conversion can raise them. ``resolve()`` returns a transient default when
    no row exists, so reading never writes on the scoring hot path.
    """

    POLICY_VERSION = "policy-v1"

    merchant = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_policy",
    )
    # Risk-level elevation cutoffs (fraud/RTO percentage 0-100).
    fraud_high_threshold = models.FloatField(default=60.0)
    fraud_medium_threshold = models.FloatField(default=30.0)
    rto_high_threshold = models.FloatField(default=70.0)
    rto_medium_threshold = models.FloatField(default=50.0)
    # Action gates.
    medium_call_rto_threshold = models.FloatField(default=50.0)
    low_call_fraud_threshold = models.FloatField(default=30.0)
    prior_rto_cancel_fraud_threshold = models.FloatField(default=20.0)
    auto_cancel_blacklisted = models.BooleanField(default=True)
    version = models.CharField(max_length=32, default=POLICY_VERSION)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "merchant risk policies"

    def __str__(self) -> str:
        return f"Risk policy for {self.merchant_id} ({self.version})"

    @classmethod
    def resolve(cls, merchant) -> "MerchantRiskPolicy":
        """Return the merchant's saved policy, or an unsaved default instance."""
        if merchant is not None:
            existing = cls.objects.filter(merchant=merchant).first()
            if existing is not None:
                return existing
        return cls(merchant=merchant)


class RiskDecisionRecord(models.Model):
    """Append-only audit of each materially-changed scoring decision.

    Together with OrderFeatureSnapshot (the inputs) this reconstructs any past
    decision point-in-time: what we knew, which policy/calibration versions
    applied, and what the engine recommended. Linked to the snapshot via
    ``feature_hash``.
    """

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="decision_records"
    )
    risk_score = models.FloatField(default=0.0)
    fraud_score = models.FloatField(default=0.0)
    rto_probability_score = models.FloatField(default=0.0)
    risk_level = models.CharField(max_length=20)
    recommended_action = models.CharField(max_length=30)
    score_source = models.CharField(max_length=20, blank=True)
    calibration_version = models.CharField(max_length=64, blank=True)
    decision_policy_version = models.CharField(max_length=32, blank=True)
    feature_schema_version = models.CharField(max_length=32, blank=True)
    feature_hash = models.CharField(max_length=64, blank=True, db_index=True)
    # ML challenger's shadow prediction at decision time (recorded even when the
    # rules remain champion, so the two can be compared on real outcomes later).
    ml_model_version = models.CharField(max_length=64, blank=True)
    ml_rto_probability = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "created_at"], name="riskdecision_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order_id} → {self.recommended_action} ({self.risk_level})"


class RiskMLModel(models.Model):
    """A trained, versioned ML challenger (serialized linear model + scaler).

    ``role`` governs how the active model is used by the scorer:
      * ``shadow`` / ``challenger`` — predicted and recorded, but the rules stay
        the champion and the decision is unchanged (safe default).
      * ``champion`` — drives the served RTO probability, with the hard rule
        guardrails (blacklist, fake-address words) still applied on top.

    Promotion is a deliberate act (``train_rto_model --promote``), only justified
    once ``evaluate_risk_engine`` shows the challenger beats the rules baseline.
    """

    TARGET_CHOICES = [("rto", "RTO")]
    ROLE_CHOICES = [
        ("shadow", "Shadow"),
        ("challenger", "Challenger"),
        ("champion", "Champion"),
    ]

    target = models.CharField(max_length=20, choices=TARGET_CHOICES, db_index=True)
    version = models.CharField(max_length=64)
    algorithm = models.CharField(max_length=40, default="logistic_regression")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="challenger")
    is_active = models.BooleanField(default=False, db_index=True)
    params = models.JSONField(default=dict)
    train_size = models.PositiveIntegerField(default=0)
    holdout_size = models.PositiveIntegerField(default=0)
    holdout_auc = models.FloatField(null=True, blank=True)
    baseline_auc = models.FloatField(null=True, blank=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-trained_at"]
        indexes = [
            models.Index(fields=["target", "is_active"], name="riskml_active_idx"),
        ]

    def __str__(self) -> str:
        state = "active" if self.is_active else "inactive"
        return f"{self.target} {self.algorithm} {self.version} [{self.role}/{state}]"
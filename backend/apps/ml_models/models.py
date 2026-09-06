"""Feature schema and aggregate models for the risk platform."""
from django.db import models


class FeatureSchemaVersion(models.Model):
    """Versioned feature contract for online and offline scoring."""

    TARGET_CHOICES = [
        ("fraud", "Fraud"),
        ("rto", "RTO"),
        ("shared", "Shared"),
    ]

    version = models.CharField(max_length=32, unique=True)
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default="shared")
    is_active = models.BooleanField(default=False)
    feature_names = models.JSONField(default=list)
    required_feature_names = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target", "is_active"], name="feat_schema_active_idx"),
        ]

    def __str__(self) -> str:
        return self.version


class FeatureAggregateWindow(models.Model):
    """Rolling aggregate metrics for reusable feature computation."""

    entity_type = models.CharField(max_length=32)
    entity_key = models.CharField(max_length=128)
    window_name = models.CharField(max_length=32)
    metrics = models.JSONField(default=dict)
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-computed_at", "-updated_at"]
        unique_together = [("entity_type", "entity_key", "window_name")]
        indexes = [
            models.Index(fields=["entity_type", "entity_key", "window_name"], name="featagg_entity_idx"),
            models.Index(fields=["window_name", "computed_at"], name="featagg_window_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_key} [{self.window_name}]"

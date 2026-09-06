"""Customer identity & behavior models."""
from django.conf import settings
from django.db import models

from .normalization import normalize_phone


class Customer(models.Model):
    """End customer who places COD orders (phone-based identity)."""

    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, db_index=True)
    normalized_phone = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    # ── Behavior tracking (updated automatically) ───────────────────────
    total_orders = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    rto_count = models.PositiveIntegerField(default=0)
    cancelled_count = models.PositiveIntegerField(default=0)
    ghosted_count = models.PositiveIntegerField(default=0)

    # ── Identity flags ──────────────────────────────────────────────────
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.CharField(max_length=200, blank=True)
    multiple_names_detected = models.BooleanField(default=False)
    names_used = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["merchant", "phone"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["merchant", "phone"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"

    def save(self, *args, **kwargs):
        self.normalized_phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    @property
    def rto_rate(self) -> float:
        """Calculate RTO rate as a percentage."""
        if self.total_orders == 0:
            return 0.0
        return round((self.rto_count / self.total_orders) * 100, 1)

    @property
    def delivery_success_rate(self) -> float:
        """Calculate delivery success rate."""
        if self.total_orders == 0:
            return 0.0
        return round((self.delivered_count / self.total_orders) * 100, 1)

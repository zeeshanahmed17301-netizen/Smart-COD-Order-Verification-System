"""Address verification models."""
from django.db import models


class Address(models.Model):
    """Delivery address with verification and geocoding data."""

    STATUS_CHOICES = [
        ("valid", "Valid"),
        ("partial", "Partial"),
        ("mismatch", "Mismatch"),
        ("high_risk", "High-Risk Locality"),
        ("unverified", "Unverified"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    full_address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    # ── Verification fields ─────────────────────────────────────────────
    validation_provider = models.CharField(max_length=50, blank=True)
    validation_verdict = models.CharField(max_length=50, blank=True)
    suggested_address = models.TextField(blank=True)
    formatted_address = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unverified"
    )
    subpremise = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=8, blank=True)
    district = models.CharField(max_length=100, blank=True)
    address_granularity = models.CharField(max_length=50, blank=True)
    deliverability_metadata = models.JSONField(default=dict, blank=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)

    # ── Geocoding ───────────────────────────────────────────────────────
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    map_preview_url = models.URLField(blank=True)

    # ── Area risk data ──────────────────────────────────────────────────
    area_rto_rate = models.FloatField(default=0.0)
    is_high_risk_area = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "addresses"
        indexes = [
            models.Index(fields=["city", "postal_code"], name="addr_city_postal_idx"),
            models.Index(fields=["country_code", "postal_code"], name="addr_country_post_idx"),
            models.Index(fields=["validation_verdict", "last_validated_at"], name="addr_verdict_valid_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_address[:50]} ({self.city})"


class CourierBranch(models.Model):
    """Courier service branch location used for reachability checks.

    Populated from scraped data (results.json) via the
    ``import_courier_branches`` management command.
    """

    brand = models.CharField(max_length=100, db_index=True)
    branch_name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)

    # Derived city fields for fast lookup
    city_normalized = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Lowercase normalized city extracted from branch_name/address.",
    )
    city_raw = models.CharField(
        max_length=100,
        blank=True,
        help_text="Original city text before normalization.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive branches are excluded from reachability checks.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["brand", "branch_name"]
        verbose_name = "courier branch"
        verbose_name_plural = "courier branches"
        indexes = [
            models.Index(
                fields=["brand", "city_normalized"],
                name="courier_brand_city_idx",
            ),
            models.Index(
                fields=["city_normalized", "is_active"],
                name="courier_city_active_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        from apps.addresses.courier_coverage import (
            extract_city_from_address,
            extract_city_from_branch_name,
            invalidate_coverage_cache,
            normalize_city,
        )

        city_source = self.city_normalized or self.city_raw
        if city_source:
            self.city_normalized = normalize_city(city_source)
        else:
            self.city_normalized = (
                extract_city_from_branch_name(self.branch_name)
                or extract_city_from_address(self.address)
            )

        super().save(*args, **kwargs)
        invalidate_coverage_cache()

    def delete(self, *args, **kwargs):
        from apps.addresses.courier_coverage import invalidate_coverage_cache

        result = super().delete(*args, **kwargs)
        invalidate_coverage_cache()
        return result

    def __str__(self) -> str:
        return f"{self.brand} — {self.branch_name}"

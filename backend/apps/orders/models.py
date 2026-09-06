"""COD Order models with risk scoring fields."""
from django.conf import settings
from django.db import models


class Order(models.Model):
    """COD order with risk analysis, scoring, and verification status."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
        ("delivered", "Delivered"),
        ("rto", "RTO"),
        ("cancelled", "Cancelled"),
    ]

    RISK_LEVEL_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    CHAT_STATUS_CHOICES = [
        ("unverified", "Unverified"),
        ("confirmed", "Confirmed"),
        ("denied", "Denied"),
        ("no_response", "No Response"),
        ("timeout", "Timeout"),
        ("failed", "Failed"),
    ]

    RECOMMENDED_ACTION_CHOICES = [
        ("ship_order", "Ship Order"),
        ("verify_address", "Verify Address"),
        ("call_customer", "Call Customer"),
        ("cancel_order", "Cancel Order"),
        ("manual_review", "Manual Review"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("prepaid", "Prepaid"),
    ]

    SCORE_SOURCE_CHOICES = [
        ("rules", "Rules"),
        ("ml", "ML"),
        ("hybrid", "Hybrid"),
        ("fallback", "Fallback"),
    ]

    # ── Core fields ─────────────────────────────────────────────────────
    order_id = models.CharField(max_length=50, unique=True, db_index=True)
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    address = models.ForeignKey(
        "addresses.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # ── Financial ───────────────────────────────────────────────────────
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod"
    )

    # ── Status & Risk ───────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    risk_score = models.FloatField(default=0.0)
    fraud_score = models.FloatField(default=0.0)
    rto_probability = models.CharField(max_length=20, default="Unknown")
    rto_probability_score = models.FloatField(default=0.0)
    score_calibration_version = models.CharField(max_length=32, blank=True, default="")
    feature_schema_version = models.CharField(max_length=32, blank=True, default="")
    fraud_model_version = models.CharField(max_length=64, blank=True, default="")
    rto_model_version = models.CharField(max_length=64, blank=True, default="")
    decision_policy_version = models.CharField(max_length=32, blank=True, default="")
    score_source = models.CharField(
        max_length=20,
        choices=SCORE_SOURCE_CHOICES,
        default="rules",
    )
    risk_level = models.CharField(
        max_length=20, choices=RISK_LEVEL_CHOICES, default="low"
    )
    address_score = models.FloatField(default=0.0)
    recommended_action = models.CharField(
        max_length=30, choices=RECOMMENDED_ACTION_CHOICES, default="manual_review"
    )
    chat_status = models.CharField(
        max_length=20, choices=CHAT_STATUS_CHOICES, default="unverified"
    )

    # ── Source tracking ─────────────────────────────────────────────────
    source = models.CharField(max_length=50, blank=True, default="manual")
    campaign = models.CharField(max_length=100, blank=True)

    # ── Timestamps ──────────────────────────────────────────────────────
    rescored_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "risk_score"]),
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["merchant", "created_at"], name="order_merchant_created_idx"),
            models.Index(fields=["merchant", "score_source", "created_at"], name="order_merchant_source_idx"),
            models.Index(fields=["feature_schema_version", "created_at"], name="order_feature_schema_idx"),
        ]

    def __str__(self) -> str:
        return f"Order {self.order_id}"


class OrderSourceSnapshot(models.Model):
    """Raw source-system fields captured during order ingestion."""

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="source_snapshot"
    )
    shopify_order_gid = models.CharField(max_length=100, blank=True, db_index=True)
    shopify_legacy_order_id = models.CharField(max_length=50, blank=True, db_index=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    browser_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_hash = models.CharField(max_length=255, blank=True)
    checkout_session_id = models.CharField(max_length=128, blank=True, db_index=True)
    device_fingerprint_id = models.CharField(max_length=128, blank=True, db_index=True)
    source_name = models.CharField(max_length=100, blank=True)
    source_identifier = models.CharField(max_length=255, blank=True)
    registered_source_url = models.URLField(blank=True)
    referrer_url = models.URLField(blank=True)
    landing_page_url = models.URLField(blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    accept_language = models.CharField(max_length=255, blank=True)
    timezone_name = models.CharField(max_length=64, blank=True)
    screen_resolution = models.CharField(max_length=32, blank=True)
    financial_status = models.CharField(max_length=50, blank=True)
    fulfillment_status = models.CharField(max_length=50, blank=True)
    billing_matches_shipping = models.BooleanField(null=True, blank=True)
    customer_journey_ready = models.BooleanField(default=False)
    customer_order_index = models.PositiveIntegerField(null=True, blank=True)
    days_to_conversion = models.FloatField(null=True, blank=True)
    shopify_risk_recommendation = models.CharField(max_length=50, blank=True)
    shopify_risk_level = models.CharField(max_length=50, blank=True)
    shopify_risk_payload = models.JSONField(default=dict, blank=True)
    risk_facts_payload = models.JSONField(default=dict, blank=True)
    raw_order_payload = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-imported_at"]
        indexes = [
            models.Index(fields=["client_ip", "imported_at"], name="ordsrc_client_ip_idx"),
            models.Index(fields=["device_fingerprint_id", "imported_at"], name="ordsrc_device_imp_idx"),
            models.Index(fields=["checkout_session_id", "imported_at"], name="ordsrc_session_imp_idx"),
            models.Index(fields=["source_name", "imported_at"], name="ordsrc_source_imp_idx"),
        ]

    def __str__(self) -> str:
        return f"Source snapshot for {self.order.order_id}"


class OrderEnrichment(models.Model):
    """Derived enrichment fields used by the scoring pipeline."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("partial", "Partial"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="enrichment"
    )
    address_provider = models.CharField(max_length=50, blank=True)
    address_validation_status = models.CharField(max_length=50, blank=True)
    normalized_address = models.TextField(blank=True)
    address_confidence = models.FloatField(default=0.0)
    address_validation_verdict = models.CharField(max_length=50, blank=True)
    address_complete = models.BooleanField(null=True, blank=True)
    address_has_unconfirmed_components = models.BooleanField(null=True, blank=True)
    address_has_inferred_components = models.BooleanField(null=True, blank=True)
    address_has_replaced_components = models.BooleanField(null=True, blank=True)
    address_possible_next_action = models.CharField(max_length=50, blank=True)
    address_precision = models.CharField(max_length=50, blank=True)
    geocode_precision = models.CharField(max_length=50, blank=True)
    geocode_granularity = models.CharField(max_length=50, blank=True)
    validation_granularity = models.CharField(max_length=50, blank=True)
    deliverability_verdict = models.CharField(max_length=50, blank=True)
    validation_metadata = models.JSONField(default=dict, blank=True)
    correction_delta_count = models.PositiveIntegerField(default=0)
    serviceable = models.BooleanField(null=True, blank=True)
    serviceability_reason = models.CharField(max_length=255, blank=True)
    ip_provider = models.CharField(max_length=50, blank=True)
    ip_risk_score = models.FloatField(default=0.0)
    ip_country = models.CharField(max_length=100, blank=True)
    ip_region = models.CharField(max_length=100, blank=True)
    ip_city = models.CharField(max_length=100, blank=True)
    ip_asn = models.CharField(max_length=32, blank=True)
    ip_isp = models.CharField(max_length=255, blank=True)
    ip_organization = models.CharField(max_length=255, blank=True)
    ip_connection_type = models.CharField(max_length=64, blank=True)
    is_anonymous = models.BooleanField(default=False)
    is_anonymous_vpn = models.BooleanField(default=False)
    is_public_proxy = models.BooleanField(default=False)
    is_residential_proxy = models.BooleanField(default=False)
    is_tor_exit_node = models.BooleanField(default=False)
    is_hosting_provider = models.BooleanField(default=False)
    ip_geo_matches_shipping_city = models.BooleanField(null=True, blank=True)
    ip_geo_matches_shipping_country = models.BooleanField(null=True, blank=True)
    repeat_ip_orders_7d = models.PositiveIntegerField(default=0)
    repeat_ip_customers_30d = models.PositiveIntegerField(default=0)
    repeat_phone_orders_30d = models.PositiveIntegerField(default=0)
    repeat_address_orders_30d = models.PositiveIntegerField(default=0)
    repeat_phone_orders_3h = models.PositiveIntegerField(default=0)
    repeat_ip_orders_3h = models.PositiveIntegerField(default=0)
    total_qty_same_phone_24h = models.PositiveIntegerField(default=0)
    total_qty_same_ip_24h = models.PositiveIntegerField(default=0)
    total_qty_same_address_24h = models.PositiveIntegerField(default=0)
    device_first_seen_at = models.DateTimeField(null=True, blank=True)
    device_order_count_30d = models.PositiveIntegerField(default=0)
    device_customer_count_30d = models.PositiveIntegerField(default=0)
    session_order_count_24h = models.PositiveIntegerField(default=0)
    email_order_count_30d = models.PositiveIntegerField(default=0)
    source_rto_rate = models.FloatField(default=0.0)
    area_rto_rate = models.FloatField(default=0.0)
    customer_rto_rate = models.FloatField(default=0.0)
    category_rto_rate = models.FloatField(default=0.0)
    contactability_score = models.FloatField(default=0.0)
    destination_postal_cluster = models.CharField(max_length=32, blank=True)
    carrier_rto_rate_30d = models.FloatField(default=0.0)
    carrier_delivery_rate_30d = models.FloatField(default=0.0)
    ndr_rate_30d = models.FloatField(default=0.0)
    estimated_delivery_days = models.FloatField(default=0.0)

    # ── Courier reachability ────────────────────────────────────────────
    courier_reachable = models.BooleanField(default=True)
    courier_reachable_count = models.PositiveIntegerField(default=0)
    courier_coverage_score = models.FloatField(default=100.0)
    courier_match_confidence = models.CharField(max_length=20, blank=True, default="")

    enrichment_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip_provider", "ip_country", "created_at"], name="orderenrich_ip_geo_idx"),
            models.Index(fields=["device_customer_count_30d", "created_at"], name="orderenrich_device_idx"),
            models.Index(fields=["destination_postal_cluster", "created_at"], name="orderenrich_postal_idx"),
        ]

    def __str__(self) -> str:
        return f"Enrichment for {self.order.order_id}"


class OrderItem(models.Model):
    """Individual line item within an order."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)
    sku = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} x{self.qty}"

    @property
    def total(self) -> float:
        return float(self.price * self.qty)


class RiskFactor(models.Model):
    """Individual risk factor contributing to an order's risk score."""

    LEVEL_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="risk_factors"
    )
    name = models.CharField(max_length=200)
    score = models.FloatField(default=0.0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-score"]

    def __str__(self) -> str:
        return f"{self.name}: {self.score} ({self.level})"


class OrderFeatureSnapshot(models.Model):
    """Immutable feature vector snapshot for scoring and training."""

    SNAPSHOT_TYPE_CHOICES = [
        ("online_scoring", "Online Scoring"),
        ("training", "Training"),
        ("backfill", "Backfill"),
    ]

    GENERATED_BY_CHOICES = [
        ("system", "System"),
        ("backfill", "Backfill"),
        ("training_job", "Training Job"),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="feature_snapshots"
    )
    feature_schema_version = models.CharField(max_length=32)
    snapshot_type = models.CharField(
        max_length=20,
        choices=SNAPSHOT_TYPE_CHOICES,
        default="online_scoring",
    )
    generated_by = models.CharField(
        max_length=30,
        choices=GENERATED_BY_CHOICES,
        default="system",
    )
    features = models.JSONField(default=dict)
    feature_hash = models.CharField(max_length=64, db_index=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["order", "generated_at"], name="ordfeat_order_gen_idx"),
            models.Index(fields=["feature_schema_version", "generated_at"], name="ordfeat_schema_gen_idx"),
            models.Index(fields=["snapshot_type", "generated_at"], name="ordfeat_type_gen_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order.order_id} [{self.feature_schema_version}]"

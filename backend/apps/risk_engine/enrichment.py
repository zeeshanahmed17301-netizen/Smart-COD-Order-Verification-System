"""Order enrichment helpers for staged risk scoring."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.addresses.courier_coverage import check_reachability
from apps.addresses.services import AddressIntelligenceService, validate_and_store
from apps.customers.normalization import normalize_phone
from apps.orders.models import Order, OrderEnrichment
from apps.orders.source_facts import build_canonical_order_facts
from apps.orders.source_ip import resolve_order_ip
from apps.risk_engine.ip_intelligence import IPIntelligenceService


# Statuses on Order.status that represent an RTO outcome
RTO_STATUS_VALUES = {"rto", "cancelled"}
# Statuses that represent a resolved order (either success or failure)
RESOLVED_STATUS_VALUES = {"delivered", "rto", "cancelled", "rejected"}

class OrderEnrichmentService:
    """Build derived order features before the final scoring pass."""

    @classmethod
    def enrich(cls, order: Order) -> OrderEnrichment:
        snapshot = getattr(order, "source_snapshot", None)
        canonical_facts = build_canonical_order_facts(order, snapshot)
        enrichment, _ = OrderEnrichment.objects.get_or_create(order=order)

        failures: list[str] = []

        try:
            cls._apply_address_features(order, enrichment)
        except Exception as exc:  # noqa: BLE001 - expose provider/config problems without fallback
            _reset_address_enrichment(enrichment)
            failures.append(str(exc)[:255])

        try:
            cls._apply_courier_reachability_features(order, enrichment)
        except Exception as exc:  # noqa: BLE001 - clear only courier evidence
            _reset_courier_enrichment(enrichment)
            failures.append(f"Courier coverage failed: {exc}"[:255])

        try:
            cls._apply_order_history_features(order, enrichment, canonical_facts)
        except Exception as exc:  # noqa: BLE001 - clear stale history rates
            _reset_history_enrichment(enrichment)
            failures.append(f"Order history enrichment failed: {exc}"[:255])

        try:
            cls._apply_ip_features(order, snapshot, enrichment, canonical_facts)
        except Exception as exc:  # noqa: BLE001 - clear only IP evidence
            _reset_ip_enrichment(enrichment)
            failures.append(str(exc)[:255])

        try:
            cls._apply_contactability_features(order, enrichment, canonical_facts)
        except Exception as exc:  # noqa: BLE001 - clear only contactability evidence
            enrichment.contactability_score = 0.0
            failures.append(f"Contactability enrichment failed: {exc}"[:255])

        if failures:
            enrichment.failure_reason = " | ".join(failures)[:255]
            enrichment.enrichment_status = "failed"
        else:
            enrichment.failure_reason = ""
            enrichment.enrichment_status = "completed"

        enrichment.enriched_at = timezone.now()
        enrichment.save()
        return enrichment

    @staticmethod
    def _apply_address_features(order: Order, enrichment: OrderEnrichment) -> None:
        # Validate/geocode against the configured external provider (e.g.
        # OpenCage) first; this persists confidence/lat-lng/status onto the
        # Address record so the heuristic below scores the enriched data. Soft
        # by design — returns None (no-op) when offline or on provider failure.
        provider_result = validate_and_store(order.address)

        result = AddressIntelligenceService.evaluate(order.address)
        enrichment.address_provider = result.provider
        enrichment.address_validation_status = result.validation_status
        enrichment.normalized_address = result.normalized_address
        enrichment.address_confidence = result.confidence
        enrichment.address_precision = result.precision
        enrichment.geocode_precision = result.geocode_precision
        enrichment.correction_delta_count = result.correction_delta_count
        enrichment.serviceable = result.serviceable
        enrichment.serviceability_reason = result.serviceability_reason
        enrichment.area_rto_rate = result.area_rto_rate

        # Derive a human-readable verdict from heuristic validation status
        _status_to_verdict = {
            "valid": "DELIVERABLE",
            "partial": "UNCONFIRMED",
            "unverified": "UNCONFIRMED",
            "mismatch": "UNDELIVERABLE",
            "high_risk": "UNDELIVERABLE",
            "missing": "UNDELIVERABLE",
        }
        enrichment.address_validation_verdict = _status_to_verdict.get(
            result.validation_status, "UNCONFIRMED"
        )

        # When an external provider validated the address, record its
        # provenance and audit fields (overriding the heuristic defaults).
        address = order.address
        if provider_result and provider_result.success and address:
            enrichment.address_provider = address.validation_provider or result.provider
            enrichment.address_confidence = address.confidence_score
            enrichment.address_validation_status = address.status
            enrichment.address_validation_verdict = address.validation_verdict or enrichment.address_validation_verdict
            enrichment.geocode_precision = provider_result.geocode_granularity or enrichment.geocode_precision
            enrichment.validation_granularity = address.address_granularity
            enrichment.validation_metadata = address.deliverability_metadata

    @staticmethod
    def _apply_courier_reachability_features(order: Order, enrichment: OrderEnrichment) -> None:
        address = order.address
        city = getattr(address, "city", "") or ""
        full_address = getattr(address, "full_address", "") or ""
        result = check_reachability(city, full_address)
        enrichment.courier_reachable = result.is_reachable
        enrichment.courier_reachable_count = len(result.reachable_couriers)
        enrichment.courier_coverage_score = result.coverage_score
        enrichment.courier_match_confidence = result.match_confidence

    @staticmethod
    def _apply_order_history_features(order: Order, enrichment: OrderEnrichment, canonical_facts: dict | None) -> None:
        from django.db.models import Sum

        now = timezone.now()
        merchant_orders = Order.objects.filter(merchant=order.merchant).exclude(id=order.id)
        recent_orders_30d = merchant_orders.filter(created_at__gte=now - timedelta(days=30))
        recent_orders_24h = merchant_orders.filter(created_at__gte=now - timedelta(hours=24))
        recent_orders_3h = merchant_orders.filter(created_at__gte=now - timedelta(hours=3))

        canonical_customer = (canonical_facts or {}).get("customer") or {}
        canonical_source = (canonical_facts or {}).get("source") or {}
        phone = normalize_phone(canonical_customer.get("phone"))
        source_name = canonical_source.get("name")
        source_orders = (
            merchant_orders.filter(source_snapshot__source_name=source_name)
            if source_name
            else merchant_orders.none()
        )
        category_names = list(order.items.values_list("category", flat=True).exclude(category=""))

        # Baseline features
        enrichment.customer_rto_rate = calculate_customer_rto_rate(
            order.customer,
            exclude_order_id=order.id,
        )
        enrichment.repeat_phone_orders_30d = (
            recent_orders_30d.filter(customer__normalized_phone=phone).count() if phone else 0
        )
        enrichment.repeat_address_orders_30d = (
            recent_orders_30d.filter(address=order.address).count() if order.address_id else 0
        )
        enrichment.source_rto_rate = calculate_rto_rate(source_orders)
        enrichment.category_rto_rate = calculate_category_rto_rate(
            merchant_orders, category_names
        )

        # Area RTO rate from REAL history for this delivery city. This overrides the
        # cold-start bootstrap value written by _apply_address_features: once the
        # merchant has a meaningful resolved sample for the city, hardcoded guesses
        # must not drive the RTO base. With too small a sample we report 0.0
        # (unknown) rather than inventing a number.
        delivery_city = (getattr(order.address, "city", "") or "").strip()
        if delivery_city:
            real_area_rate = calculate_area_rto_rate(merchant_orders, delivery_city)
            if real_area_rate is not None:
                enrichment.area_rto_rate = real_area_rate

        # Velocity features
        ip_address = None
        snapshot = getattr(order, "source_snapshot", None)
        if snapshot:
            order_ip = resolve_order_ip(
                client_ip=snapshot.client_ip,
                browser_ip=snapshot.browser_ip,
                raw_order_payload=snapshot.raw_order_payload,
            )
            ip_address = order_ip["value"]

        # Phone velocity
        enrichment.repeat_phone_orders_3h = (
            recent_orders_3h.filter(customer__normalized_phone=phone).count() if phone else 0
        )
        phone_orders_24h = recent_orders_24h.filter(customer__normalized_phone=phone) if phone else merchant_orders.none()
        enrichment.total_qty_same_phone_24h = phone_orders_24h.aggregate(total=Sum("items__qty"))["total"] or 0

        # IP velocity
        if ip_address:
            ip_orders_3h = recent_orders_3h.filter(
                Q(source_snapshot__client_ip=ip_address) | Q(source_snapshot__browser_ip=ip_address)
            )
            ip_orders_24h = recent_orders_24h.filter(
                Q(source_snapshot__client_ip=ip_address) | Q(source_snapshot__browser_ip=ip_address)
            )
            enrichment.repeat_ip_orders_3h = ip_orders_3h.count()
            enrichment.total_qty_same_ip_24h = ip_orders_24h.aggregate(total=Sum("items__qty"))["total"] or 0
        else:
            enrichment.repeat_ip_orders_3h = 0
            enrichment.total_qty_same_ip_24h = 0

        # Address velocity
        if order.address_id:
            address_orders_24h = recent_orders_24h.filter(address=order.address)
            enrichment.total_qty_same_address_24h = address_orders_24h.aggregate(total=Sum("items__qty"))["total"] or 0
        else:
            enrichment.total_qty_same_address_24h = 0

    @staticmethod
    def _apply_ip_features(
        order: Order,
        snapshot,
        enrichment: OrderEnrichment,
        canonical_facts: dict | None,
    ) -> None:
        # No IP evidence → leave geo-match UNKNOWN (None). We must never fabricate
        # a "matches shipping city/country = True" here: that is a fake signal that
        # silently *lowers* the fraud/RTO score for orders we actually know nothing
        # about. Unknown stays unknown so the scorer treats it neutrally.
        if not snapshot:
            _reset_ip_enrichment(enrichment)
            return

        order_ip = resolve_order_ip(
            client_ip=snapshot.client_ip,
            browser_ip=snapshot.browser_ip,
            raw_order_payload=snapshot.raw_order_payload,
        )
        ip_address = order_ip["value"]
        if not ip_address:
            _reset_ip_enrichment(enrichment)
            return

        canonical_addresses = (canonical_facts or {}).get("addresses") or {}
        shipping_address = canonical_addresses.get("shipping_address") or {}
        shipping_city = shipping_address.get("city") or getattr(order.address, "city", None)
        shipping_country = shipping_address.get("country")
        intelligence = IPIntelligenceService.evaluate(
            ip_address=ip_address,
            shipping_city=shipping_city,
            shipping_country=shipping_country,
        )

        recent_week = Order.objects.filter(
            merchant=order.merchant,
            created_at__gte=timezone.now() - timedelta(days=7),
        ).exclude(id=order.id).filter(
            Q(source_snapshot__client_ip=ip_address)
            | Q(source_snapshot__browser_ip=ip_address)
        )
        recent_month = Order.objects.filter(
            merchant=order.merchant,
            created_at__gte=timezone.now() - timedelta(days=30),
        ).exclude(id=order.id).filter(
            Q(source_snapshot__client_ip=ip_address)
            | Q(source_snapshot__browser_ip=ip_address)
        )

        enrichment.repeat_ip_orders_7d = recent_week.count()
        enrichment.repeat_ip_customers_30d = (
            recent_month.values("customer_id").distinct().count()
        )
        enrichment.ip_provider = intelligence.provider
        enrichment.ip_city = intelligence.city
        enrichment.ip_region = intelligence.region
        enrichment.ip_country = intelligence.country
        enrichment.is_anonymous = intelligence.is_anonymous
        enrichment.is_anonymous_vpn = intelligence.is_anonymous_vpn
        enrichment.is_public_proxy = intelligence.is_public_proxy
        enrichment.is_residential_proxy = intelligence.is_residential_proxy
        enrichment.is_tor_exit_node = intelligence.is_tor_exit_node
        enrichment.is_hosting_provider = intelligence.is_hosting_provider
        enrichment.ip_geo_matches_shipping_city = intelligence.geo_matches_shipping_city
        enrichment.ip_geo_matches_shipping_country = intelligence.geo_matches_shipping_country
        enrichment.ip_risk_score = round(
            max(
                _derive_ip_risk_score(enrichment),
                float(intelligence.risk_score or 0.0),
            ),
            1,
        )

    @staticmethod
    def _apply_contactability_features(order: Order, enrichment: OrderEnrichment, canonical_facts: dict | None) -> None:
        canonical_customer = (canonical_facts or {}).get("customer") or {}
        phone = canonical_customer.get("phone")
        email = canonical_customer.get("email")
        score = 0.0
        if phone:
            score += 45
        if email:
            score += 20
        if order.chat_status == "confirmed":
            score += 35
        elif order.chat_status == "unverified":
            score += 10
        elif order.chat_status == "no_response":
            score -= 15
        elif order.chat_status == "timeout":
            # Customer ignored the verification window entirely — a confirmed ghost.
            score -= 20
        elif order.chat_status == "denied":
            # Customer explicitly refused the order — they will not take delivery.
            score -= 25
        elif order.chat_status == "failed":
            # WhatsApp message failed delivery — stronger unreachability signal
            # than no_response (no_response could mean user hasn't replied yet)
            score -= 20

        enrichment.contactability_score = max(0.0, min(score, 100.0))


def calculate_rto_rate(queryset) -> float:
    resolved_orders = queryset.filter(status__in=RESOLVED_STATUS_VALUES)
    total = resolved_orders.count()
    if total == 0:
        return 0.0
    rto = resolved_orders.filter(status__in=RTO_STATUS_VALUES).count()
    return round((rto / total) * 100, 1)


def calculate_customer_rto_rate(customer, *, exclude_order_id: int | None = None) -> float:
    queryset = customer.orders.all()
    if exclude_order_id is not None:
        queryset = queryset.exclude(id=exclude_order_id)
    return calculate_rto_rate(queryset)


#: Minimum resolved orders in an area before its historical RTO rate is trusted.
AREA_RTO_MIN_SAMPLE = 5


def calculate_area_rto_rate(queryset, city: str) -> float | None:
    """RTO rate (%) for a delivery city from real resolved orders.

    Returns ``None`` when the city is empty or the resolved sample is below
    ``AREA_RTO_MIN_SAMPLE`` — the caller then leaves the existing value untouched
    rather than scoring on a statistically meaningless (or fabricated) rate.
    """
    city_key = (city or "").strip()
    if not city_key:
        return None

    area_orders = queryset.filter(address__city__iexact=city_key)
    resolved = area_orders.filter(status__in=RESOLVED_STATUS_VALUES)
    total = resolved.count()
    if total < AREA_RTO_MIN_SAMPLE:
        return None
    rto = resolved.filter(status__in=RTO_STATUS_VALUES).count()
    return round((rto / total) * 100, 1)


def calculate_category_rto_rate(queryset, categories: list[str]) -> float:
    if not categories:
        return 0.0

    matching_orders = queryset.filter(items__category__in=categories).distinct()
    return calculate_rto_rate(matching_orders)


def _derive_ip_risk_score(enrichment: OrderEnrichment) -> float:
    """Build a bounded IP risk score from observed velocity and network signals."""
    score = 0.0

    repeat_orders = max(int(enrichment.repeat_ip_orders_7d or 0), 0)
    repeat_customers = max(int(enrichment.repeat_ip_customers_30d or 0), 0)

    # The fraud signal is *multiple different customers from the same IP* (fraud
    # ring or bulk-order abuse). A single customer placing multiple orders from
    # the same IP is normal COD repeat-purchase behaviour and must NOT inflate
    # the score — this was causing every Shopify-synced order to score high
    # because they all share the same Shopify webhook origin IP.
    if repeat_orders >= 2 and repeat_customers >= 2:
        # Multiple distinct customers + high order volume = strong fraud-ring signal
        score += min(35.0, repeat_orders * 8.0)
    elif repeat_orders >= 4 and repeat_customers == 0:
        # Unusual order burst from a single-customer IP with no customer data
        score += min(12.0, repeat_orders * 2.0)

    if repeat_customers >= 2:
        score += min(45.0, repeat_customers * 12.0)

    proxy_flags = [
        enrichment.is_anonymous,
        enrichment.is_anonymous_vpn,
        enrichment.is_public_proxy,
        enrichment.is_residential_proxy,
        enrichment.is_tor_exit_node,
        enrichment.is_hosting_provider,
    ]
    proxy_count = sum(1 for flag in proxy_flags if flag)
    if proxy_count:
        score += min(35.0, 18.0 + (proxy_count * 7.0))

    if enrichment.ip_geo_matches_shipping_city is False:
        score += 10.0
    if enrichment.ip_geo_matches_shipping_country is False:
        score += 20.0

    return round(min(score, 100.0), 1)


def _reset_ip_enrichment(enrichment: OrderEnrichment) -> None:
    enrichment.ip_provider = "internal_observed"
    enrichment.ip_risk_score = 0.0
    enrichment.ip_city = ""
    enrichment.ip_region = ""
    enrichment.ip_country = ""
    enrichment.is_anonymous = False
    enrichment.is_anonymous_vpn = False
    enrichment.is_public_proxy = False
    enrichment.is_residential_proxy = False
    enrichment.is_tor_exit_node = False
    enrichment.is_hosting_provider = False
    enrichment.ip_geo_matches_shipping_city = None
    enrichment.ip_geo_matches_shipping_country = None
    enrichment.repeat_ip_orders_7d = 0
    enrichment.repeat_ip_customers_30d = 0


def _reset_address_enrichment(enrichment: OrderEnrichment) -> None:
    """Clear stale address evidence when address validation fails."""
    enrichment.address_provider = ""
    enrichment.address_validation_status = ""
    enrichment.normalized_address = ""
    enrichment.address_confidence = 0.0
    enrichment.address_precision = ""
    enrichment.geocode_precision = ""
    enrichment.address_validation_verdict = ""
    enrichment.address_complete = None
    enrichment.address_has_unconfirmed_components = None
    enrichment.address_has_inferred_components = None
    enrichment.address_has_replaced_components = None
    enrichment.validation_granularity = ""
    enrichment.validation_metadata = {}
    enrichment.correction_delta_count = 0
    enrichment.serviceable = None
    enrichment.serviceability_reason = ""
    enrichment.area_rto_rate = 0.0


def _reset_courier_enrichment(enrichment: OrderEnrichment) -> None:
    """Clear stale courier evidence when courier matching fails."""
    enrichment.courier_reachable = False
    enrichment.courier_reachable_count = 0
    enrichment.courier_coverage_score = 0.0
    enrichment.courier_match_confidence = ""


def _reset_history_enrichment(enrichment: OrderEnrichment) -> None:
    """Clear stale history evidence when historical enrichment fails."""
    enrichment.source_rto_rate = 0.0
    enrichment.customer_rto_rate = 0.0
    enrichment.category_rto_rate = 0.0

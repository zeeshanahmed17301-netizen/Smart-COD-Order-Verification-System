"""Immutable, versioned feature vector captured at scoring time.

This is the point-in-time record of *what the engine knew when it decided* — the
audit trail for any past decision and the training matrix for an offline model.
Capturing it at scoring time (before the courier outcome exists) is what keeps a
future model leak-free: a snapshot never sees its own label.

The feature contract is the ordered ``FEATURE_NAMES`` list below. A test asserts
that ``build_feature_vector`` emits exactly these keys so the contract and the
builder can never silently drift apart.
"""

from __future__ import annotations

import hashlib
import json

# Bump when the feature set changes. Snapshots and the FeatureSchemaVersion row
# carry this so offline consumers can filter to a single, consistent contract.
FEATURE_SCHEMA_VERSION = "rg-features-v1"

# The feature contract, in a stable order. Keep in sync with build_feature_vector
# (guarded by test_feature_vector_matches_declared_contract).
FEATURE_NAMES: list[str] = [
    # — phone —
    "phone_valid",
    "phone_suspicious",
    "phone_repeat_customer",
    # — name —
    "name_suspicious",
    "name_common",
    # — address —
    "address_structured",
    "address_has_keyword",
    "address_vague",
    "address_blacklisted",
    "address_confidence",
    # — courier —
    "courier_available",          # 1 yes / 0 no / null unknown
    "courier_coverage_score",
    "courier_reachable_count",
    # — customer history (point-in-time, pre-outcome) —
    "total_orders",
    "delivered_count",
    "rto_count",
    "cancelled_count",
    "ghosted_count",
    "customer_rto_rate",
    "is_blacklisted",
    "multiple_names_detected",
    "history_has_previous_rto",
    "history_has_successful_deliveries",
    "history_is_first_order",
    # — geographic / source priors —
    "area_rto_rate",
    "source_rto_rate",
    "category_rto_rate",
    # — network / device —
    "ip_risk_score",
    "ip_geo_matches_shipping_city",   # 1 / 0 / null
    "is_proxy_or_vpn",
    "repeat_phone_orders_3h",
    "repeat_ip_orders_3h",
    "repeat_phone_orders_30d",
    "velocity_peak",
    # — contactability —
    "contactability_score",
    "chat_status",
    "chat_unreachable",
    # — order —
    "amount",
    "is_cod",
    "item_count",
    "total_qty",
    # — external platform risk —
    "shopify_recommendation",
    "shopify_risk_level",
]


def _tri(value) -> int | None:
    """Map a tri-state boolean (True/False/None) to 1/0/None for ML use."""
    if value is None:
        return None
    return 1 if value else 0


def build_feature_vector(
    *,
    order,
    enrichment,
    snapshot,
    phone_result: dict,
    name_result: dict,
    address_result: dict,
    courier_result: dict,
    history_result: dict,
    customer_signals: dict,
    chat_failed: bool,
    velocity_peak: int,
) -> dict:
    """Assemble the flat feature dict from already-computed scoring inputs."""
    items = list(order.items.all())
    chat_status = getattr(order, "chat_status", "") or ""

    features = {
        "phone_valid": int(bool(phone_result["valid"])),
        "phone_suspicious": int(bool(phone_result["is_suspicious"])),
        "phone_repeat_customer": int(bool(phone_result["repeat_customer"])),
        "name_suspicious": int(bool(name_result["is_suspicious"])),
        "name_common": int(bool(name_result["is_common_name"])),
        "address_structured": int(bool(address_result["is_structured"])),
        "address_has_keyword": int(bool(address_result["has_keyword"])),
        "address_vague": int(bool(address_result["is_vague"])),
        "address_blacklisted": int(bool(address_result["has_blacklist_word"])),
        "address_confidence": round(float(getattr(enrichment, "address_confidence", 0.0) or 0.0), 2),
        "courier_available": _tri(courier_result["is_available"]),
        "courier_coverage_score": round(float(getattr(enrichment, "courier_coverage_score", 0.0) or 0.0), 2),
        "courier_reachable_count": int(getattr(enrichment, "courier_reachable_count", 0) or 0),
        "total_orders": int(getattr(order.customer, "total_orders", 0) or 0),
        "delivered_count": int(getattr(order.customer, "delivered_count", 0) or 0),
        "rto_count": int(getattr(order.customer, "rto_count", 0) or 0),
        "cancelled_count": int(customer_signals.get("cancelled", 0) or 0),
        "ghosted_count": int(customer_signals.get("ghosted", 0) or 0),
        "customer_rto_rate": round(float(getattr(enrichment, "customer_rto_rate", 0.0) or 0.0), 2),
        "is_blacklisted": int(bool(customer_signals.get("blacklisted", False))),
        "multiple_names_detected": int(bool(customer_signals.get("multiple_names", False))),
        "history_has_previous_rto": int(bool(history_result["has_previous_rto"])),
        "history_has_successful_deliveries": int(bool(history_result["has_successful_deliveries"])),
        "history_is_first_order": int(bool(history_result["is_first_order"])),
        "area_rto_rate": round(float(getattr(enrichment, "area_rto_rate", 0.0) or 0.0), 2),
        "source_rto_rate": round(float(getattr(enrichment, "source_rto_rate", 0.0) or 0.0), 2),
        "category_rto_rate": round(float(getattr(enrichment, "category_rto_rate", 0.0) or 0.0), 2),
        "ip_risk_score": round(float(getattr(enrichment, "ip_risk_score", 0.0) or 0.0), 2),
        "ip_geo_matches_shipping_city": _tri(getattr(enrichment, "ip_geo_matches_shipping_city", None)),
        "is_proxy_or_vpn": int(any([
            bool(getattr(enrichment, "is_anonymous", False)),
            bool(getattr(enrichment, "is_anonymous_vpn", False)),
            bool(getattr(enrichment, "is_public_proxy", False)),
            bool(getattr(enrichment, "is_residential_proxy", False)),
            bool(getattr(enrichment, "is_tor_exit_node", False)),
            bool(getattr(enrichment, "is_hosting_provider", False)),
        ])),
        "repeat_phone_orders_3h": int(getattr(enrichment, "repeat_phone_orders_3h", 0) or 0),
        "repeat_ip_orders_3h": int(getattr(enrichment, "repeat_ip_orders_3h", 0) or 0),
        "repeat_phone_orders_30d": int(getattr(enrichment, "repeat_phone_orders_30d", 0) or 0),
        "velocity_peak": int(velocity_peak or 0),
        "contactability_score": round(float(getattr(enrichment, "contactability_score", 0.0) or 0.0), 2),
        "chat_status": chat_status,
        "chat_unreachable": int(bool(chat_failed) or chat_status in {"timeout", "no_response", "denied"}),
        "amount": round(float(getattr(order, "amount", 0) or 0), 2),
        "is_cod": int(getattr(order, "payment_method", "cod") == "cod"),
        "item_count": len(items),
        "total_qty": int(sum(int(getattr(i, "qty", 0) or 0) for i in items)),
        "shopify_recommendation": (getattr(snapshot, "shopify_risk_recommendation", "") or "").upper(),
        "shopify_risk_level": (getattr(snapshot, "shopify_risk_level", "") or "").upper(),
    }
    return features


def feature_hash(features: dict) -> str:
    """Stable SHA-256 over the feature dict — used to dedup identical snapshots
    and to verify a stored snapshot has not been tampered with."""
    canonical = json.dumps(features, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

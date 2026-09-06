"""Rule-based risk scoring services."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from django.utils import timezone

from apps.orders.models import Order, OrderFeatureSnapshot, RiskFactor
from apps.orders.source_facts import build_canonical_order_facts
from apps.risk_engine.enrichment import OrderEnrichmentService
from apps.risk_engine.models import MerchantRiskPolicy, RiskDecisionRecord
from apps.risk_engine.features import (
    FEATURE_SCHEMA_VERSION,
    build_feature_vector,
    feature_hash,
)
from apps.risk_engine.validators import (
    validate_address,
    validate_courier,
    validate_name,
    validate_order_history,
    validate_phone,
)


logger = logging.getLogger(__name__)

RULE_ENGINE_VERSION = "rule-based-v1"


@dataclass
class RiskResult:
    """Result from a risk scoring calculation."""

    address_score: float
    fraud_score: float
    rto_probability_score: float
    rto_probability: str
    risk_score: float
    risk_level: str
    recommended_action: str
    factors: list[dict]
    score_breakdown: dict
    decision_summary: dict
    information_quality: dict
    calibration_version: str
    feature_schema_version: str
    decision_policy_version: str
    score_source: str
    features: dict
    ml_model_version: str = ""
    ml_rto_probability: float | None = None


@dataclass
class CalibratedProbabilityResult:
    """Compatibility payload for order serializers."""

    version: str
    target: str
    probability: float
    confidence_low: float
    confidence_high: float
    sample_size: int
    score_range: tuple[float, float]
    source: str
    is_estimated: bool


def _factor(name: str, score: float, level: str, description: str) -> dict:
    return {
        "name": name,
        "score": round(float(score), 2),
        "level": level,
        "description": description,
    }


def _risk_level_from_score(score: float) -> str:
    if score >= 4:
        return "low"
    if score >= 1:
        return "medium"
    return "high"


def _rto_probability_label(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    if score >= 15:
        return "Low"
    return "Very Low"


def _action_from_results(*, risk_level: str, address_result: dict, courier_result: dict, history_result: dict, fraud_score: float, rto_score: float, policy) -> str:
    # Hard cancellation triggers regardless of risk level
    if address_result["has_blacklist_word"]:
        return "cancel_order"
    if history_result["has_previous_rto"] and fraud_score >= policy.prior_rto_cancel_fraud_threshold:
        return "cancel_order"
    if risk_level == "high":
        return "cancel_order"
    if risk_level == "medium":
        if courier_result["is_available"] is False:
            return "call_customer"
        if rto_score >= policy.medium_call_rto_threshold:
            return "call_customer"
        return "verify_address"
    # low risk — but still flag if fraud signal is present
    if fraud_score >= policy.low_call_fraud_threshold:
        return "call_customer"
    return "ship_order"


def _level_label(level: str) -> str:
    return {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }.get(level, str(level or "").title())


def _score_band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 25:
        return "Guarded"
    return "Low"


def _address_confidence_label(score: float) -> str:
    if score >= 85:
        return "Strong"
    if score >= 65:
        return "Usable"
    if score >= 45:
        return "Weak"
    return "Poor"


def _action_label(action: str) -> str:
    return {
        "ship_order": "Ship Order",
        "verify_address": "Verify Address",
        "call_customer": "Call Customer",
        "cancel_order": "Cancel Order",
        "manual_review": "Manual Review",
    }.get(action, str(action or "").replace("_", " ").title())


def build_score_breakdown(*, order: Order, enrichment=None, result: RiskResult | None = None) -> dict:
    """Return a serializer-friendly breakdown of the persisted decision."""
    fraud_score = float(result.fraud_score if result else order.fraud_score)
    address_score = float(result.address_score if result else order.address_score)
    rto_score = float(result.rto_probability_score if result else order.rto_probability_score)
    risk_score = float(result.risk_score if result else order.risk_score)
    risk_level = result.risk_level if result else order.risk_level
    recommended_action = result.recommended_action if result else order.recommended_action
    calibration_version = result.calibration_version if result else order.score_calibration_version

    fraud_calibration = ScoreCalibrationService.calibrate(
        target="fraud",
        score=fraud_score,
        version=calibration_version,
    )
    rto_calibration = ScoreCalibrationService.calibrate(
        target="rto",
        score=rto_score,
        version=calibration_version,
    )

    return {
        "overall": {
            "score": risk_score,
            "label": _level_label(risk_level),
        },
        "fraud": {
            "score": fraud_score,
            "label": _score_band(fraud_score),
            "probability": fraud_calibration.probability,
            "confidence_interval": {
                "lower": fraud_calibration.confidence_low,
                "upper": fraud_calibration.confidence_high,
            },
            "sample_size": fraud_calibration.sample_size,
            "score_range": {
                "min": fraud_calibration.score_range[0],
                "max": fraud_calibration.score_range[1],
            },
        },
        "address": {
            "score": address_score,
            "label": _address_confidence_label(address_score),
            "risk_score": round(max(0.0, 100.0 - address_score), 1),
        },
        "rto": {
            "score": rto_score,
            "label": _rto_probability_label(rto_score),
            "probability": rto_calibration.probability,
            "confidence_interval": {
                "lower": rto_calibration.confidence_low,
                "upper": rto_calibration.confidence_high,
            },
            "sample_size": rto_calibration.sample_size,
            "score_range": {
                "min": rto_calibration.score_range[0],
                "max": rto_calibration.score_range[1],
            },
        },
        "operational": {
            "source_rto_rate": float(getattr(enrichment, "source_rto_rate", 0.0) or 0.0),
            "area_rto_rate": float(getattr(enrichment, "area_rto_rate", 0.0) or 0.0),
            "customer_rto_rate": float(getattr(enrichment, "customer_rto_rate", 0.0) or 0.0),
            "category_rto_rate": float(getattr(enrichment, "category_rto_rate", 0.0) or 0.0),
            "contactability_score": float(getattr(enrichment, "contactability_score", 0.0) or 0.0),
            "courier_reachable": getattr(enrichment, "courier_reachable", None) if enrichment else None,
            "courier_reachable_count": int(getattr(enrichment, "courier_reachable_count", 0) or 0),
            "courier_coverage_score": float(getattr(enrichment, "courier_coverage_score", 0.0) or 0.0),
            "enrichment_status": getattr(enrichment, "enrichment_status", "") if enrichment else "",
            "failure_reason": getattr(enrichment, "failure_reason", "") if enrichment else "",
        },
        "calibration": {
            "version": rto_calibration.version or calibration_version,
            "source": rto_calibration.source,
            "fraud_source": fraud_calibration.source,
            "is_estimated": fraud_calibration.is_estimated or rto_calibration.is_estimated,
        },
        "provenance": {
            "score_source": order.score_source,
            "feature_schema_version": order.feature_schema_version,
            "decision_policy_version": order.decision_policy_version,
            "recommended_action": recommended_action,
            "computed_at": order.rescored_at or order.updated_at,
        },
    }


def build_decision_summary(*, risk_level: str, recommended_action: str, factors: list[dict], information_quality: dict, order: Order | None = None) -> dict:
    primary_reasons = [factor["name"] for factor in factors[:3]]
    return {
        "headline": f"{risk_level.title()} risk order",
        "recommended_action": recommended_action,
        "recommended_action_label": _action_label(recommended_action),
        "primary_driver": primary_reasons[0] if primary_reasons else "No major risk signal",
        "primary_reasons": primary_reasons,
        "coverage_label": information_quality.get("coverage_label", "fair"),
        "warnings": information_quality.get("warnings", []),
        "order_status": getattr(order, "status", "") if order else "",
    }


class InformationQualityService:
    """Summarize evidence quality without external validation dependencies."""

    @staticmethod
    def score(order, enrichment, snapshot, canonical_facts=None) -> dict:
        warnings: list[str] = []
        coverage_score = 100.0

        if not getattr(order, "address_id", None):
            coverage_score -= 35
            warnings.append("Missing delivery address.")
        elif not getattr(order.address, "postal_code", ""):
            coverage_score -= 8
            warnings.append("Postal code is missing, reducing address confidence.")

        if not getattr(order.customer, "phone", ""):
            coverage_score -= 25
            warnings.append("Missing customer phone number.")

        if enrichment and enrichment.enrichment_status == "failed":
            coverage_score -= 20
            warnings.append(enrichment.failure_reason or "Order enrichment failed.")
        elif enrichment and enrichment.enrichment_status != "completed":
            coverage_score -= 10
            warnings.append("Order enrichment is incomplete.")

        if snapshot is None:
            coverage_score -= 10
            warnings.append("No source snapshot available.")

        if canonical_facts:
            customer = canonical_facts.get("customer") or {}
            if not customer.get("name"):
                coverage_score -= 10
                warnings.append("Customer name is incomplete in source data.")
            if not customer.get("phone"):
                coverage_score -= 10
                warnings.append("Canonical customer phone is missing in source data.")

        coverage_score = max(0.0, round(coverage_score, 1))
        if coverage_score >= 80:
            coverage_label = "strong"
        elif coverage_score >= 55:
            coverage_label = "fair"
        else:
            coverage_label = "weak"

        return {
            "coverage_score": coverage_score,
            "coverage_label": coverage_label,
            "warnings": warnings,
            "has_source_snapshot": bool(snapshot),
            "has_chat_confirmation": order.chat_status == "confirmed",
            "enrichment_status": getattr(enrichment, "enrichment_status", "missing") if enrichment else "missing",
        }


class ScoreCalibrationService:
    """Serve outcome-backed score→probability calibration.

    When a ``RiskCalibrationModel`` has been fitted (via ``evaluate_risk_engine
    --fit``) the probability is the observed rate for that score band. Until then
    it returns an explicitly-flagged ``uncalibrated`` pass-through rather than a
    fake confidence.
    """

    @staticmethod
    def get_active_version() -> str:
        from apps.risk_engine.calibration import _active_model

        model = _active_model("rto") or _active_model("fraud")
        return model.version if model else RULE_ENGINE_VERSION

    @staticmethod
    def calibrate(*, target: str, score: float, version: str | None = None) -> CalibratedProbabilityResult:
        from apps.risk_engine.calibration import serve

        served = serve(target, score, default_version=version or RULE_ENGINE_VERSION)
        return CalibratedProbabilityResult(
            version=served.version,
            target=target,
            probability=served.probability,
            confidence_low=served.confidence_low,
            confidence_high=served.confidence_high,
            sample_size=served.sample_size,
            score_range=served.score_range,
            source=served.source,
            is_estimated=served.is_estimated,
        )


class RiskScoringEngine:
    """Rule-based risk engine with enrichment-backed extra signals."""

    @classmethod
    def calculate(cls, order: Order, config=None) -> RiskResult:
        del config

        snapshot = getattr(order, "source_snapshot", None)
        canonical_facts = build_canonical_order_facts(order, snapshot) or {}
        enrichment = OrderEnrichmentService.enrich(order)

        customer_data = canonical_facts.get("customer") or {}
        address_data = canonical_facts.get("addresses") or {}
        customer_name = customer_data.get("name") or order.customer.name
        customer_phone = customer_data.get("phone") or order.customer.phone
        address_city = address_data.get("city") or getattr(order.address, "city", "") or order.customer.city
        full_address = getattr(order.address, "full_address", "") or ""
        district = getattr(order.address, "district", "") or ""

        phone_result = validate_phone(
            customer_phone,
            prior_order_count=max(
                int(order.customer.total_orders or 0),
                int(getattr(enrichment, "repeat_phone_orders_30d", 0) or 0) + 1,
            ),
        )
        name_result = validate_name(customer_name)
        address_result = validate_address(full_address, address_city, district)
        courier_result = validate_courier(
            reachable=getattr(enrichment, "courier_reachable", None),
            coverage_score=float(getattr(enrichment, "courier_coverage_score", 0.0) or 0.0),
        )
        history_result = validate_order_history(
            total_orders=int(order.customer.total_orders or 0),
            delivered_count=int(order.customer.delivered_count or 0),
            rto_count=int(order.customer.rto_count or 0),
        )

        # --- Customer behavioural history (per-customer pattern signals) ---
        # These were tracked on the Customer model but never scored. They are the
        # strongest personalised RTO/fraud predictors we have.
        customer = order.customer
        cust_blacklisted = bool(getattr(customer, "is_blacklisted", False))
        cust_blacklist_reason = (getattr(customer, "blacklist_reason", "") or "").strip()
        cust_multiple_names = bool(getattr(customer, "multiple_names_detected", False))
        cust_cancelled = int(getattr(customer, "cancelled_count", 0) or 0)
        cust_ghosted = int(getattr(customer, "ghosted_count", 0) or 0)
        cust_rto_rate = float(getattr(customer, "rto_rate", 0.0) or 0.0)

        rule_score = (
            phone_result["score_delta"]
            + name_result["score_delta"]
            + address_result["score_delta"]
            + courier_result["score_delta"]
            + history_result["score_delta"]
        )

        extra_adjustments = {
            "proxy_or_vpn": 0,
            "velocity_spike": 0,
            "shopify_risk": 0,
        }
        extra_factors: list[dict] = []

        proxy_flags = [
            bool(getattr(enrichment, "is_anonymous", False)),
            bool(getattr(enrichment, "is_anonymous_vpn", False)),
            bool(getattr(enrichment, "is_public_proxy", False)),
            bool(getattr(enrichment, "is_residential_proxy", False)),
            bool(getattr(enrichment, "is_tor_exit_node", False)),
            bool(getattr(enrichment, "is_hosting_provider", False)),
        ]
        if any(proxy_flags):
            extra_adjustments["proxy_or_vpn"] = -1
            extra_factors.append(
                _factor(
                    "Proxy or VPN Source",
                    20,
                    "medium",
                    "The source IP is marked as proxy, VPN, TOR, or hosting traffic.",
                )
            )

        velocity_peak = max(
            int(getattr(enrichment, "repeat_phone_orders_3h", 0) or 0),
            int(getattr(enrichment, "repeat_ip_orders_3h", 0) or 0),
        )
        if velocity_peak >= 3:
            extra_adjustments["velocity_spike"] = -1
            extra_factors.append(
                _factor(
                    "High Order Velocity",
                    18,
                    "medium",
                    "Three or more recent orders came from the same phone or IP in three hours.",
                )
            )

        recommendation = (getattr(snapshot, "shopify_risk_recommendation", "") or "").upper()
        shopify_risk_level = (getattr(snapshot, "shopify_risk_level", "") or "").upper()
        if recommendation == "CANCEL":
            extra_adjustments["shopify_risk"] = -2
            extra_factors.append(
                _factor(
                    "Shopify High-Risk Recommendation",
                    35,
                    "high",
                    "Shopify recommends cancelling this order.",
                )
            )
        elif recommendation == "INVESTIGATE" or shopify_risk_level in {"HIGH", "SEVERE"}:
            extra_adjustments["shopify_risk"] = -1
            extra_factors.append(
                _factor(
                    "Shopify Investigation Signal",
                    20,
                    "medium",
                    "Shopify has flagged the order for manual investigation.",
                )
            )

        rule_score += sum(extra_adjustments.values())

        # --- enrichment-derived signals (read once for reuse) ---
        _e_ip_geo_match = getattr(enrichment, "ip_geo_matches_shipping_city", None)
        _e_ip_risk = float(getattr(enrichment, "ip_risk_score", 0.0) or 0.0)
        _e_addr_conf = float(getattr(enrichment, "address_confidence", 75.0) or 75.0)
        _e_contact = float(getattr(enrichment, "contactability_score", 65.0) or 65.0)
        _e_area_rto = float(getattr(enrichment, "area_rto_rate", 0.0) or 0.0)
        _e_source_rto = float(getattr(enrichment, "source_rto_rate", 0.0) or 0.0)
        _e_customer_rto = float(getattr(enrichment, "customer_rto_rate", 0.0) or 0.0)
        _e_coverage = float(getattr(enrichment, "courier_coverage_score", 0.0) or 0.0)
        _order_amount = float(getattr(order, "amount", 0) or 0)
        # chat_status=failed is a hard contactability failure (message undeliverable),
        # stronger than no_response — tracked separately for explicit scoring bumps.
        # Also check Conversation.status because order.chat_status may lag behind
        # (e.g. stays "unverified" while the actual conversation record is "failed").
        _chat_failed = (getattr(order, "chat_status", "") == "failed")
        if not _chat_failed:
            try:
                from apps.chatbot.models import Conversation as _Conv
                _conv = _Conv.objects.filter(order=order).only("status").first()
                if _conv and _conv.status == "failed":
                    _chat_failed = True
            except Exception:
                pass

        factors: list[dict] = []
        if phone_result["valid"]:
            factors.append(_factor("Valid Phone Number", 10, "low", "Phone number passed the base rule checks."))
        if phone_result["is_suspicious"]:
            factors.append(_factor("Suspicious Phone Pattern", 30, "high", "Phone format, repetition, or sequential digits look suspicious."))
        if phone_result["repeat_customer"]:
            factors.append(_factor("Frequent Phone Reuse", 15, "medium", "The same phone number has placed more than three orders."))
        if name_result["is_suspicious"]:
            factors.append(_factor("Suspicious Customer Name", 25, "medium", "The customer name is too short, contains digits, or looks fabricated."))
        elif name_result["is_common_name"]:
            factors.append(_factor("Recognized Customer Name", 8, "low", "The customer name resembles a common Pakistani name."))
        if address_result["is_structured"] and address_result["has_keyword"]:
            factors.append(_factor("Structured Address", 12, "low", "The address contains enough structure for delivery review."))
        else:
            factors.append(_factor("Weak Address", 28, "high", "The address is incomplete, too short, or missing delivery keywords."))
        if not address_result["has_keyword"]:
            factors.append(_factor("No Address Keyword", 20, "high", "Address lacks a deliverable reference (Street, Road, Colony, Block, etc.)."))
        if address_result["is_vague"]:
            factors.append(_factor("Vague Address Language", 18, "medium", "The address description is vague and may need manual confirmation."))
        if address_result["has_blacklist_word"]:
            factors.append(_factor("Blacklisted Address Terms", 40, "high", "The address contains fake or joke keywords."))
        if courier_result["is_available"] is True:
            cov_pct = courier_result["coverage_score"]
            if cov_pct >= 100:
                factors.append(_factor("Full Courier Coverage", 10, "low", "All matched couriers fully cover the delivery area."))
            else:
                factors.append(_factor("Partial Courier Coverage", 8, "medium", f"Courier coverage is {cov_pct:.0f}% — some risk of delivery failure."))
        elif courier_result["is_available"] is False:
            factors.append(_factor("Courier Coverage Missing", 40, "high", "No courier branch was matched for the delivery area."))
        if history_result["has_previous_rto"]:
            rto_detail = (
                f"The customer has prior return-to-origin history "
                f"({cust_rto_rate:.0f}% RTO rate)." if cust_rto_rate > 0
                else "The customer has prior return-to-origin history."
            )
            factors.append(_factor("Previous RTO History", 35, "high", rto_detail))
        elif history_result["has_successful_deliveries"]:
            factors.append(_factor("Successful Delivery History", 12, "low", "The customer has successful past deliveries."))
        elif history_result["is_first_order"]:
            factors.append(_factor("First-Time Order", 6, "low", "No prior delivery history available for this customer."))
        # Per-customer behavioural pattern factors
        if cust_blacklisted:
            factors.append(_factor(
                "Blacklisted Customer", 50, "high",
                cust_blacklist_reason or "This customer has been blacklisted by the merchant.",
            ))
        if cust_multiple_names:
            factors.append(_factor(
                "Multiple Names On Same Number", 22, "medium",
                "This phone number has placed orders under different customer names.",
            ))
        if cust_ghosted >= 2:
            factors.append(_factor(
                "Repeated Non-Response", round(min(cust_ghosted * 6.0, 20.0), 1), "medium",
                f"The customer ignored verification on {cust_ghosted} prior orders.",
            ))
        if cust_cancelled >= 2:
            factors.append(_factor(
                "Frequent Cancellations", round(min(cust_cancelled * 4.0, 16.0), 1), "medium",
                f"The customer cancelled {cust_cancelled} prior orders.",
            ))
        if _chat_failed:
            factors.append(_factor("WhatsApp Confirmation Failed", 16, "medium", "WhatsApp message could not be delivered — customer is unreachable."))
        # Enrichment-based factors
        if _e_ip_geo_match is False:
            factors.append(_factor("IP–Delivery City Mismatch", 14, "medium", "The browsing IP resolved to a different city than the delivery address."))
        if _e_ip_risk > 20:
            factors.append(_factor("Elevated IP Risk Score", round(_e_ip_risk * 0.4, 1), "medium", f"IP intelligence reports a risk score of {_e_ip_risk:.0f}."))
        if _e_addr_conf < 60:
            factors.append(_factor("Low Address Confidence", 18, "high", f"Address confidence is only {_e_addr_conf:.0f}% — delivery failure risk is elevated."))
        elif _e_addr_conf < 75:
            factors.append(_factor("Moderate Address Confidence", 10, "medium", f"Address confidence is {_e_addr_conf:.0f}% (unconfirmed) — minor delivery risk."))
        if _e_contact < 30:
            factors.append(_factor("Very Low Contactability", 20, "high", f"Contactability score of {_e_contact:.0f} — customer is difficult to reach."))
        elif _e_contact < 55:
            factors.append(_factor("Low Contactability", 10, "medium", f"Contactability score of {_e_contact:.0f} — customer may be hard to reach."))
        if _e_area_rto >= 20:
            factors.append(_factor("High-RTO Delivery Area", round(_e_area_rto * 0.5, 1), "high", f"This delivery area has a {_e_area_rto:.0f}% historical RTO rate."))
        elif _e_area_rto >= 10:
            factors.append(_factor("Moderate-RTO Delivery Area", round(_e_area_rto * 0.4, 1), "medium", f"This delivery area has a {_e_area_rto:.0f}% historical RTO rate."))
        factors.extend(extra_factors)

        address_score = 100.0
        if not address_result["is_structured"]:
            address_score -= 40.0
        if not address_result["has_keyword"]:
            address_score -= 20.0
        if address_result["is_vague"]:
            address_score -= 15.0
        if address_result["has_blacklist_word"]:
            address_score -= 35.0
        if courier_result["is_available"] is False:
            address_score -= 30.0
        elif courier_result["is_available"] is True:
            address_score += 5.0
        # Enrichment-backed address confidence refines score
        if _e_addr_conf < 60:
            address_score -= 20.0
        elif _e_addr_conf < 75:
            address_score -= 8.0
        address_score = round(max(0.0, min(address_score, 100.0)), 1)

        # ------------------------------------------------------------------ #
        # Fraud score                                                          #
        # Combines rule-based signals (phone/name/address patterns) with      #
        # enrichment-backed signals (IP geo, ip_risk, contactability).        #
        # ------------------------------------------------------------------ #
        fraud_score = 0.0
        # Rule-based signals (strong — hard fraud indicators)
        if phone_result["is_suspicious"]:
            fraud_score += 35.0
        if name_result["is_suspicious"]:
            fraud_score += 20.0
        if address_result["has_blacklist_word"]:
            fraud_score += 30.0
        if extra_adjustments["proxy_or_vpn"]:
            fraud_score += 15.0
        if extra_adjustments["velocity_spike"]:
            fraud_score += 12.0
        if extra_adjustments["shopify_risk"] == -2:
            fraud_score += 22.0
        elif extra_adjustments["shopify_risk"] == -1:
            fraud_score += 12.0
        if history_result["has_previous_rto"]:
            fraud_score += 10.0
        # Per-customer fraud signals
        if cust_blacklisted:
            # A merchant-blacklisted customer is a hard fraud indicator.
            fraud_score += 40.0
        if cust_multiple_names:
            # Same number, different names = identity inconsistency / account sharing.
            fraud_score += 12.0
        # new-requirements.md: no valid address keyword → High Risk (address is unverifiable)
        if not address_result["has_keyword"]:
            fraud_score += 15.0
        # new-requirements.md rule: same phone >3 orders = Medium Risk
        if phone_result["repeat_customer"]:
            fraud_score += 10.0
        # WhatsApp delivery failure = hard contactability failure (distinct from no_response)
        if _chat_failed:
            fraud_score += 8.0
        # Enrichment-backed signals (softer — probabilistic fraud signals)
        if _e_ip_geo_match is False:
            # In Pakistan, ~80% of real orders come from mobile data in a different
            # city. Use a moderate weight (+8) rather than a heavy one — real fraud
            # is identified by combining this with other signals, not alone.
            fraud_score += 8.0
        if _e_ip_risk > 20:
            fraud_score += min(_e_ip_risk * 0.4, 20.0)
        if _e_contact < 30:
            # Very hard to reach — characteristic of ghost/prank COD orders
            fraud_score += 15.0
        elif _e_contact < 50:
            fraud_score += 6.0
        # Trust offset: recognized common Pakistani name slightly lowers fraud probability
        # (new-requirements.md: names matching common valid names → Low Risk)
        if name_result["is_common_name"] and not name_result["is_suspicious"]:
            fraud_score = max(0.0, fraud_score - 5.0)
        fraud_score = round(max(0.0, min(fraud_score, 100.0)), 1)

        # ------------------------------------------------------------------ #
        # RTO probability score                                                #
        # Rule signals give binary on/off bumps; enrichment rates give a      #
        # data-driven base reflecting real area/source/customer history.      #
        # ------------------------------------------------------------------ #
        rto_probability_score = 0.0
        # Environmental base: area and source RTO rates reflect historical data
        rto_probability_score += _e_area_rto * 0.65
        rto_probability_score += _e_source_rto * 0.30
        # Customer-specific history (strong personalised signal)
        if _e_customer_rto > 0:
            rto_probability_score += _e_customer_rto * 0.50
        # Strong rule-based signals
        if history_result["has_previous_rto"]:
            rto_probability_score += 35.0
        # Per-customer behavioural history — repeated ghosting and cancellations are
        # direct precursors to a return-to-origin.
        if cust_ghosted >= 1:
            rto_probability_score += min(cust_ghosted * 6.0, 20.0)
        if cust_cancelled >= 1:
            rto_probability_score += min(cust_cancelled * 4.0, 16.0)
        if not address_result["is_structured"]:
            rto_probability_score += 20.0
        if address_result["is_vague"]:
            rto_probability_score += 12.0
        # Courier availability
        if courier_result["is_available"] is False:
            rto_probability_score += 38.0
        elif courier_result["is_available"] is True and _e_coverage < 100:
            rto_probability_score += 5.0  # partial coverage = small extra risk
        # Enrichment-backed softer signals
        if _e_ip_geo_match is False:
            # Geo mismatch hints the delivery city may be wrong
            rto_probability_score += 8.0
        if _e_addr_conf < 60:
            rto_probability_score += 15.0
        elif _e_addr_conf < 75:
            rto_probability_score += 8.0
        if _e_contact < 45:
            rto_probability_score += 10.0
        elif _e_contact >= 80:
            rto_probability_score -= 5.0
        # WhatsApp delivery failure means the merchant cannot call back on issues
        if _chat_failed:
            rto_probability_score += 10.0
        # High-value COD orders have higher customer refusal rates
        if _order_amount >= 10000:
            rto_probability_score += 8.0
        elif _order_amount >= 5000:
            rto_probability_score += 4.0
        # Order-history adjustments
        if history_result["is_first_order"]:
            rto_probability_score += 7.0
        if history_result["has_successful_deliveries"]:
            rto_probability_score -= 15.0
        rto_probability_score = round(max(0.0, min(rto_probability_score, 100.0)), 1)

        policy = MerchantRiskPolicy.resolve(getattr(order, "merchant", None))

        features = build_feature_vector(
            order=order,
            enrichment=enrichment,
            snapshot=snapshot,
            phone_result=phone_result,
            name_result=name_result,
            address_result=address_result,
            courier_result=courier_result,
            history_result=history_result,
            customer_signals={
                "blacklisted": cust_blacklisted,
                "multiple_names": cust_multiple_names,
                "cancelled": cust_cancelled,
                "ghosted": cust_ghosted,
                "rto_rate": cust_rto_rate,
            },
            chat_failed=_chat_failed,
            velocity_peak=velocity_peak,
        )

        # ML challenger (RTO). Predicted in shadow by default: recorded for later
        # comparison against outcomes, but the rules stay champion and the decision
        # is unchanged. Only a model explicitly promoted to 'champion' drives the
        # served RTO probability — and even then the hard rule guardrails below
        # (blacklist, fake-address words) still apply on top.
        ml_model_version = ""
        ml_rto_probability = None
        score_source = "rules"
        try:
            from apps.risk_engine.ml import MLChallenger

            ml_prediction = MLChallenger.predict("rto", features)
        except Exception:
            logger.exception("ML challenger prediction failed for %s", order.order_id)
            ml_prediction = None
        if ml_prediction is not None:
            ml_model_version = ml_prediction.version
            ml_rto_probability = round(ml_prediction.probability * 100.0, 1)
            if ml_prediction.role == "champion":
                rto_probability_score = ml_rto_probability
                score_source = "hybrid"

        final_risk_level = _risk_level_from_score(rule_score)
        # Elevate risk_level when fraud or RTO percentage thresholds are hit.
        # The rule_score (validator delta-based) can stay "low" even when enriched
        # signals push fraud past the merchant's threshold. Percentages take
        # precedence. Thresholds come from the merchant's risk policy (governable).
        if (
            cust_blacklisted
            or fraud_score >= policy.fraud_high_threshold
            or rto_probability_score >= policy.rto_high_threshold
        ):
            final_risk_level = "high"
        elif (
            fraud_score >= policy.fraud_medium_threshold
            or rto_probability_score >= policy.rto_medium_threshold
        ):
            if final_risk_level == "low":
                final_risk_level = "medium"
        recommended_action = _action_from_results(
            risk_level=final_risk_level,
            address_result=address_result,
            courier_result=courier_result,
            history_result=history_result,
            fraud_score=fraud_score,
            rto_score=rto_probability_score,
            policy=policy,
        )
        # A blacklisted customer is a hard cancel when the policy enforces it.
        if cust_blacklisted and policy.auto_cancel_blacklisted:
            recommended_action = "cancel_order"

        information_quality = InformationQualityService.score(order, enrichment, snapshot, canonical_facts)

        result = RiskResult(
            address_score=address_score,
            fraud_score=fraud_score,
            rto_probability_score=rto_probability_score,
            rto_probability=_rto_probability_label(rto_probability_score),
            risk_score=float(rule_score),
            risk_level=final_risk_level,
            recommended_action=recommended_action,
            factors=factors,
            score_breakdown={
                "base_rules": {
                    "phone": phone_result["score_delta"],
                    "name": name_result["score_delta"],
                    "address": address_result["score_delta"],
                    "courier": courier_result["score_delta"],
                    "history": history_result["score_delta"],
                },
                "extra_adjustments": extra_adjustments,
            },
            decision_summary={},
            information_quality=information_quality,
            calibration_version=RULE_ENGINE_VERSION,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            decision_policy_version=policy.version,
            score_source=score_source,
            features=features,
            ml_model_version=ml_model_version,
            ml_rto_probability=ml_rto_probability,
        )
        result.decision_summary = build_decision_summary(
            risk_level=result.risk_level,
            recommended_action=result.recommended_action,
            factors=result.factors,
            information_quality=result.information_quality,
            order=order,
        )
        return result

    @classmethod
    def score_and_save(cls, order: Order, *, skip_chatbot: bool = False) -> RiskResult:
        result = cls.calculate(order)

        order.risk_score = result.risk_score
        order.fraud_score = result.fraud_score
        order.rto_probability = result.rto_probability
        order.rto_probability_score = result.rto_probability_score
        order.score_calibration_version = result.calibration_version
        order.feature_schema_version = result.feature_schema_version
        order.fraud_model_version = ""
        order.rto_model_version = ""
        order.decision_policy_version = result.decision_policy_version
        order.score_source = result.score_source
        order.risk_level = result.risk_level
        order.address_score = result.address_score
        order.recommended_action = result.recommended_action
        order.rescored_at = timezone.now()
        order.save(
            update_fields=[
                "risk_score",
                "fraud_score",
                "rto_probability",
                "rto_probability_score",
                "score_calibration_version",
                "feature_schema_version",
                "fraud_model_version",
                "rto_model_version",
                "decision_policy_version",
                "score_source",
                "risk_level",
                "address_score",
                "recommended_action",
                "rescored_at",
                "updated_at",
            ]
        )

        RiskFactor.objects.filter(order=order).delete()
        RiskFactor.objects.bulk_create(
            [
                RiskFactor(
                    order=order,
                    name=factor["name"],
                    score=factor["score"],
                    level=factor["level"],
                    description=factor["description"],
                )
                for factor in result.factors
            ]
        )

        digest = feature_hash(result.features)
        cls._persist_feature_snapshot(order, result, digest)
        cls._persist_decision_record(order, result, digest)

        if not skip_chatbot:
            try:
                from apps.chatbot.services import ConversationService

                ConversationService.auto_trigger_if_needed(order, result)
            except Exception:
                logger.exception("Failed to auto-trigger WhatsApp verification for %s", order.order_id)

        return result

    @staticmethod
    def _persist_feature_snapshot(order: Order, result: RiskResult, digest: str) -> None:
        """Append an immutable feature snapshot, skipping no-op re-scores.

        Only writes when the feature hash differs from the order's latest
        snapshot, so idempotent re-scores don't flood the audit history while
        every genuine change in inputs is recorded point-in-time.
        """
        latest = (
            OrderFeatureSnapshot.objects.filter(order=order)
            .order_by("-generated_at")
            .values_list("feature_hash", flat=True)
            .first()
        )
        if latest == digest:
            return
        try:
            OrderFeatureSnapshot.objects.create(
                order=order,
                feature_schema_version=result.feature_schema_version or FEATURE_SCHEMA_VERSION,
                snapshot_type="online_scoring",
                generated_by="system",
                features=result.features,
                feature_hash=digest,
            )
        except Exception:
            # Snapshotting is an audit side-effect — never let it break scoring.
            logger.exception("Failed to persist feature snapshot for %s", order.order_id)

    @staticmethod
    def _persist_decision_record(order: Order, result: RiskResult, digest: str) -> None:
        """Append a decision audit record when the decision materially changes.

        "Material" = a change in the recommended action, risk level, or any of the
        three scores vs. the order's latest record. Pairs with the feature
        snapshot (linked by ``feature_hash``) for full point-in-time replay.
        """
        latest = order.decision_records.order_by("-created_at").first()
        if latest is not None and (
            latest.recommended_action == result.recommended_action
            and latest.risk_level == result.risk_level
            and latest.risk_score == result.risk_score
            and latest.fraud_score == result.fraud_score
            and latest.rto_probability_score == result.rto_probability_score
        ):
            return
        try:
            RiskDecisionRecord.objects.create(
                order=order,
                risk_score=result.risk_score,
                fraud_score=result.fraud_score,
                rto_probability_score=result.rto_probability_score,
                risk_level=result.risk_level,
                recommended_action=result.recommended_action,
                score_source=result.score_source,
                calibration_version=result.calibration_version,
                decision_policy_version=result.decision_policy_version,
                feature_schema_version=result.feature_schema_version,
                feature_hash=digest,
                ml_model_version=result.ml_model_version,
                ml_rto_probability=result.ml_rto_probability,
            )
        except Exception:
            logger.exception("Failed to persist decision record for %s", order.order_id)
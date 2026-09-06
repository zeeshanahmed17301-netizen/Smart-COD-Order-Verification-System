"""Address intelligence helpers used by the risk pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class AddressIntelligenceResult:
    """Normalized address intelligence used by enrichment and scoring."""

    provider: str
    validation_status: str
    normalized_address: str
    confidence: float
    precision: str
    geocode_precision: str
    correction_delta_count: int
    serviceable: bool | None
    serviceability_reason: str
    area_rto_rate: float


def _label_to_confidence(status: str) -> float:
    mapping = {
        "valid": 95.0,
        "partial": 70.0,
        "mismatch": 35.0,
        "high_risk": 20.0,
        "unverified": 55.0,
    }
    return mapping.get(status or "", 0.0)


def _has_real_value(value) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.casefold() not in {
        "-",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "not available",
    }


def _address_completeness(address) -> tuple[float, int]:
    completed_fields = 0
    if _has_real_value(address.full_address):
        completed_fields += 1
    if _has_real_value(address.city):
        completed_fields += 1
    if _has_real_value(address.province):
        completed_fields += 1
    if _has_real_value(address.postal_code):
        completed_fields += 1

    return round((completed_fields / 4) * 100, 1), completed_fields


def count_corrections(original: str, normalized: str) -> int:
    """Approximate how much a normalized address diverges from the raw input."""
    original_tokens = {
        token.strip().lower() for token in (original or "").split(",") if token.strip()
    }
    normalized_tokens = {
        token.strip().lower() for token in (normalized or "").split(",") if token.strip()
    }
    return len(normalized_tokens.symmetric_difference(original_tokens))


def _evaluate_with_heuristic(address) -> AddressIntelligenceResult:
    completeness_score, completed_fields = _address_completeness(address)
    derived_confidence = address.confidence_score or _label_to_confidence(address.status)
    normalized_address = address.suggested_address or address.full_address
    geocode_precision = "rooftop" if address.latitude and address.longitude else ""
    serviceable = not (address.is_high_risk_area or address.status == "high_risk")

    return AddressIntelligenceResult(
        provider="internal_heuristic",
        validation_status=address.status,
        normalized_address=normalized_address,
        confidence=round((derived_confidence * 0.7) + (completeness_score * 0.3), 1),
        precision="premise"
        if completed_fields >= 4
        else "locality"
        if completed_fields >= 2
        else "partial",
        geocode_precision=geocode_precision,
        correction_delta_count=count_corrections(address.full_address, normalized_address),
        serviceable=serviceable,
        serviceability_reason="" if serviceable else "Marked as high-risk locality",
        area_rto_rate=address.area_rto_rate,
    )


class AddressIntelligenceService:
    """Build normalized address evidence from the stored address record."""

    @staticmethod
    def evaluate(address) -> AddressIntelligenceResult:
        if not address:
            return AddressIntelligenceResult(
                provider="internal_heuristic",
                validation_status="missing",
                normalized_address="",
                confidence=0.0,
                precision="missing",
                geocode_precision="",
                correction_delta_count=0,
                serviceable=None,
                serviceability_reason="No address available",
                area_rto_rate=0.0,
            )

        return _evaluate_with_heuristic(address)


# ─── External provider validation + persistence ──────────────────────────────

# Maps the configured provider name to its validation service.
def _get_validation_service(provider: str):
    if provider == "opencage":
        from apps.addresses.opencage_validation import OpenCageAddressValidationService

        return OpenCageAddressValidationService, "opencage"
    if provider == "google":
        from apps.addresses.google_validation import GoogleAddressValidationService

        return GoogleAddressValidationService, "google_address_validation"
    return None, ""


def _is_validation_fresh(address, provider_name: str) -> bool:
    """True if the address was already validated by this provider recently."""
    freshness_days = getattr(settings, "ADDRESS_VALIDATION_FRESHNESS_DAYS", 30)
    if freshness_days <= 0 or not address.last_validated_at:
        return False
    if address.validation_provider != provider_name:
        return False
    return address.last_validated_at >= timezone.now() - timedelta(days=freshness_days)


def validate_and_store(address):
    """Validate ``address`` via the configured external provider and persist it.

    Returns the provider result on a successful, freshly-fetched validation, or
    ``None`` when no external provider is configured, the cached result is still
    fresh, or the provider call fails (the record is left untouched so the
    internal heuristic can score it). Provider failures are intentionally soft —
    they never raise — so external outages don't block order enrichment.
    """
    if not address or not (address.full_address or "").strip():
        return None

    provider = str(getattr(settings, "ADDRESS_VALIDATION_PROVIDER", "internal_heuristic")).strip().lower()
    service, provider_name = _get_validation_service(provider)
    if service is None:
        return None  # internal_heuristic / unknown → offline scoring only

    if _is_validation_fresh(address, provider_name):
        return None

    region_code = (address.country_code or "PK").strip() or "PK"
    result = service.validate(address.full_address, region_code=region_code)
    if not result.success:
        logger.warning(
            "Address validation via %s failed for address %s: %s",
            provider_name,
            address.pk,
            result.error,
        )
        return None

    # Over-specified strings (e.g. "House 12, Street 5, F-7, Islamabad") often
    # fail to geocode even when the area is real. Fall back to the structured
    # city so a resolvable area still earns a partial signal instead of 0.
    if (
        result.latitude is None
        and _has_real_value(address.city)
        and address.city.strip().casefold() != (address.full_address or "").strip().casefold()
    ):
        city_result = service.validate(address.city, region_code=region_code)
        if city_result.success and city_result.latitude is not None:
            # Cap city-level hits at "partial" — we only confirmed the area,
            # not the specific premise the customer gave.
            if city_result.status == "valid":
                city_result.status = "partial"
                city_result.verdict = "UNCONFIRMED_BUT_PLAUSIBLE"
                city_result.confidence_score = min(city_result.confidence_score, 60.0)
            result = city_result

    _persist_validation_result(address, result, provider_name)
    return result


def _persist_validation_result(address, result, provider_name: str) -> None:
    """Write a provider validation result onto the Address record."""
    address.validation_provider = provider_name
    address.validation_verdict = result.verdict or ""
    address.confidence_score = result.confidence_score
    address.status = result.status or "unverified"
    address.address_granularity = result.validation_granularity or ""
    address.last_validated_at = timezone.now()

    if result.formatted_address:
        address.formatted_address = result.formatted_address
        address.suggested_address = result.formatted_address
    if result.latitude is not None and result.longitude is not None:
        address.latitude = result.latitude
        address.longitude = result.longitude

    # Only backfill structured components we don't already have — never clobber
    # what the merchant/customer originally supplied.
    if not _has_real_value(address.city) and result.city:
        address.city = result.city
    if not _has_real_value(address.province) and result.province:
        address.province = result.province
    if not _has_real_value(address.postal_code) and result.postal_code:
        address.postal_code = result.postal_code
    if not _has_real_value(address.district) and result.district:
        address.district = result.district
    if not _has_real_value(address.country_code) and result.country_code:
        address.country_code = result.country_code

    address.deliverability_metadata = {
        "provider": provider_name,
        "verdict": result.verdict,
        "confidence_score": result.confidence_score,
        "geocode_granularity": result.geocode_granularity,
        "result": result.raw_response,
    }
    address.save()
"""Google Address Validation API client.

Calls Google's Address Validation REST endpoint to normalize, validate,
and geocode delivery addresses. API failures are returned explicitly so
the caller can mark enrichment failed instead of using silent substitutes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_API_URL = "https://addressvalidation.googleapis.com/v1:validateAddress"

# ── Verdict → status mapping ─────────────────────────────────────────────────
_VERDICT_STATUS_MAP = {
    "CONFIRMED": "valid",
    "UNCONFIRMED_BUT_PLAUSIBLE": "partial",
    "UNCONFIRMED_AND_SUSPICIOUS": "mismatch",
    "UNRESOLVED": "mismatch",
    "UNUSED_TOKEN": "partial",
}

# ── Granularity → confidence contribution ─────────────────────────────────────
_GRANULARITY_SCORES = {
    "SUB_PREMISE": 98,
    "PREMISE": 95,
    "PREMISE_PROXIMITY": 85,
    "BLOCK": 75,
    "ROUTE": 65,
    "OTHER": 40,
}


@dataclass
class GoogleValidationResult:
    """Structured result from the Google Address Validation API."""

    verdict: str = ""
    validation_granularity: str = ""
    geocode_granularity: str = ""
    address_complete: bool = False
    has_unconfirmed_components: bool = False
    has_inferred_components: bool = False
    has_replaced_components: bool = False
    formatted_address: str = ""
    city: str = ""
    province: str = ""
    postal_code: str = ""
    country_code: str = ""
    subpremise: str = ""
    district: str = ""
    latitude: float | None = None
    longitude: float | None = None
    confidence_score: float = 0.0
    status: str = "unverified"
    raw_response: dict = field(default_factory=dict)
    success: bool = False
    error: str = ""


class GoogleAddressValidationService:
    """Call the Google Address Validation API and parse the response."""

    @classmethod
    def validate(cls, full_address: str, region_code: str = "PK") -> GoogleValidationResult:
        """Validate a single address string against Google's API.

        Returns a populated ``GoogleValidationResult`` on success, or a
        result with ``success=False`` and an ``error`` message on failure.
        """
        api_key = getattr(settings, "GOOGLE_ADDRESS_VALIDATION_API_KEY", "")
        if not api_key:
            return GoogleValidationResult(
                success=False,
                error="GOOGLE_ADDRESS_VALIDATION_API_KEY not configured",
            )

        timeout = getattr(settings, "GOOGLE_ADDRESS_VALIDATION_TIMEOUT", 5)

        payload = {
            "address": {
                "regionCode": region_code,
                "addressLines": [full_address],
            },
        }

        try:
            response = requests.post(
                _API_URL,
                params={"key": api_key},
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.warning("Google Address Validation API timed out for: %s", full_address[:80])
            return GoogleValidationResult(
                success=False,
                error=f"Google Address Validation API timed out after {timeout}s",
            )
        except requests.exceptions.RequestException as exc:
            error_message = _request_error_message(exc)
            logger.warning(
                "Google Address Validation API error for %s: %s",
                full_address[:80],
                error_message,
            )
            return GoogleValidationResult(success=False, error=error_message)

        return cls._parse_response(data)

    @classmethod
    def _parse_response(cls, data: dict) -> GoogleValidationResult:
        """Parse the raw Google API response into a structured result."""
        result_data = data.get("result", {})
        verdict_data = result_data.get("verdict", {})
        address_data = result_data.get("address", {})
        geocode_data = result_data.get("geocode", {})

        # ── Verdict ──────────────────────────────────────────────────
        verdict = verdict_data.get("validationGranularity", "OTHER")
        input_granularity = verdict_data.get("inputGranularity", "")
        address_complete = verdict_data.get("addressComplete", False)
        has_unconfirmed = verdict_data.get("hasUnconfirmedComponents", False)
        has_inferred = verdict_data.get("hasInferredComponents", False)
        has_replaced = verdict_data.get("hasReplacedComponents", False)

        # ── Formatted address ────────────────────────────────────────
        formatted = address_data.get("formattedAddress", "")

        # ── Extract structured components ────────────────────────────
        components = address_data.get("addressComponents", [])
        city = ""
        province = ""
        postal_code = ""
        country_code = ""
        subpremise = ""
        district = ""

        for component in components:
            component_type = component.get("componentType", "")
            component_name = component.get("componentName", {})
            text = component_name.get("text", "")

            if component_type == "locality":
                city = text
            elif component_type == "administrative_area_level_1":
                province = text
            elif component_type == "postal_code":
                postal_code = text
            elif component_type == "country":
                country_code = component_name.get("languageCode", text)
            elif component_type == "subpremise":
                subpremise = text
            elif component_type == "sublocality_level_1":
                district = text
            elif component_type in ("administrative_area_level_2", "sublocality") and not district:
                district = text

        # ── Geocode ──────────────────────────────────────────────────
        location = geocode_data.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        # ── Derive overall confidence score ──────────────────────────
        # Combine verdict quality, granularity, and component confirmation
        base_score = _GRANULARITY_SCORES.get(verdict, 40)

        # Verdict-level adjustments
        overall_verdict = _derive_overall_verdict(verdict_data, components)
        if overall_verdict == "CONFIRMED":
            confidence = min(base_score + 5, 100)
        elif overall_verdict == "UNCONFIRMED_BUT_PLAUSIBLE":
            confidence = min(base_score - 10, 80)
        elif overall_verdict == "UNCONFIRMED_AND_SUSPICIOUS":
            confidence = min(base_score - 30, 50)
        else:
            confidence = max(base_score - 40, 10)

        # Penalties
        if has_unconfirmed:
            confidence = max(confidence - 10, 5)
        if has_replaced:
            confidence = max(confidence - 5, 5)
        if not address_complete:
            confidence = max(confidence - 15, 5)

        confidence = round(min(max(confidence, 0.0), 100.0), 1)

        # ── Map verdict to status ────────────────────────────────────
        status = _VERDICT_STATUS_MAP.get(overall_verdict, "unverified")

        # ── Geocode granularity ──────────────────────────────────────
        place_types = geocode_data.get("placeTypes", [])
        geocode_granularity = "rooftop" if "premise" in place_types else (
            "range_interpolated" if "route" in place_types else ""
        )

        return GoogleValidationResult(
            verdict=overall_verdict,
            validation_granularity=verdict,
            geocode_granularity=geocode_granularity,
            address_complete=address_complete,
            has_unconfirmed_components=has_unconfirmed,
            has_inferred_components=has_inferred,
            has_replaced_components=has_replaced,
            formatted_address=formatted,
            city=city,
            province=province,
            postal_code=postal_code,
            country_code=country_code,
            subpremise=subpremise,
            district=district,
            latitude=latitude,
            longitude=longitude,
            confidence_score=confidence,
            status=status,
            raw_response=data,
            success=True,
        )


def _derive_overall_verdict(verdict_data: dict, components: list[dict]) -> str:
    """Derive an overall address verdict from component-level confirmations.

    Google doesn't give a single top-level verdict string directly.  Instead,
    we infer it from ``addressComplete``, ``validationGranularity``, and
    individual component confirmation levels.
    """
    if verdict_data.get("addressComplete"):
        # Check if most components are confirmed
        confirmed = sum(
            1 for c in components
            if c.get("confirmationLevel") == "CONFIRMED"
        )
        total = len(components) or 1
        if confirmed / total >= 0.7:
            return "CONFIRMED"
        return "UNCONFIRMED_BUT_PLAUSIBLE"

    has_unconfirmed = verdict_data.get("hasUnconfirmedComponents", False)
    granularity = verdict_data.get("validationGranularity", "OTHER")

    if granularity in ("PREMISE", "SUB_PREMISE", "PREMISE_PROXIMITY"):
        return "UNCONFIRMED_BUT_PLAUSIBLE" if has_unconfirmed else "CONFIRMED"
    if granularity in ("BLOCK", "ROUTE"):
        return "UNCONFIRMED_BUT_PLAUSIBLE"
    return "UNRESOLVED"


def _request_error_message(exc: requests.exceptions.RequestException) -> str:
    """Return an actionable Google API error without leaking the API key."""
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    google_message = ""

    if response is not None:
        try:
            payload = response.json()
            google_message = payload.get("error", {}).get("message", "")
        except ValueError:
            google_message = ""

    if status_code == 403:
        parts = [
            "Google Address Validation API returned 403 Forbidden.",
            "Check that Address Validation API is enabled for the Google Cloud project, billing is active, and API key restrictions allow this backend server and API.",
        ]
        if google_message:
            parts.append(f"Google message: {google_message}")
        return " ".join(parts)

    if status_code:
        message = f"Google Address Validation API returned HTTP {status_code}."
        if google_message:
            message = f"{message} Google message: {google_message}"
        return message

    return f"Google Address Validation API request failed: {exc.__class__.__name__}"

"""OpenCage geocoding/validation client.

OpenCage (https://opencagedata.com) wraps OpenStreetMap and other open
datasets. It does not return a deliverability verdict like Google's Address
Validation API, so we treat its match precision (``confidence`` 1-10) plus
component resolution as a validation proxy. API failures are surfaced
explicitly so the caller can fall back to the internal heuristic instead of
persisting silent substitutes.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.addresses.google_validation import GoogleValidationResult

logger = logging.getLogger(__name__)

_API_URL = "https://api.opencagedata.com/geocode/v1/json"

# NOTE: OpenCage ``confidence`` (1-10) reflects the *precision* of the match
# (bounding-box size), NOT whether the address is real — a whole city scores
# low precisely because its box is large. So validity is driven by which
# components resolved (premise > street > city), with confidence only nudging
# borderline street-level hits.
_CONFIDENCE_STREET_VALID = 7

# Component ``_type`` values that indicate a precise (premise/street) hit.
_PREMISE_TYPES = {"building", "address", "house", "premise"}
_STREET_TYPES = {"road", "street", "pedestrian"}

# Granularity → confidence score contributed to the Address record (0-100).
_GRANULARITY_SCORE = {
    "PREMISE": 95.0,
    "ROUTE": 80.0,
    "BLOCK": 60.0,
    "OTHER": 30.0,
}


class OpenCageAddressValidationService:
    """Call the OpenCage geocoding API and parse it into a validation result."""

    @classmethod
    def validate(cls, full_address: str, region_code: str = "PK") -> GoogleValidationResult:
        """Geocode/validate a single address string against OpenCage.

        Returns a populated ``GoogleValidationResult`` on success, or a result
        with ``success=False`` and an ``error`` message on failure. The shared
        result dataclass keeps downstream consumers provider-agnostic.
        """
        api_key = getattr(settings, "OPENCAGE_API_KEY", "")
        if not api_key:
            return GoogleValidationResult(
                success=False,
                error="OPENCAGE_API_KEY not configured",
            )

        address = (full_address or "").strip()
        if not address:
            return GoogleValidationResult(success=False, error="Empty address")

        timeout = getattr(settings, "ADDRESS_VALIDATION_TIMEOUT_SECONDS", 5)
        params = {
            "q": address,
            "key": api_key,
            "limit": 1,
            "no_annotations": 1,
            "countrycode": (region_code or "PK").lower(),
        }

        try:
            response = requests.get(_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.warning("OpenCage API timed out for: %s", address[:80])
            return GoogleValidationResult(
                success=False,
                error=f"OpenCage API timed out after {timeout}s",
            )
        except requests.exceptions.RequestException as exc:
            error_message = _request_error_message(exc)
            logger.warning("OpenCage API error for %s: %s", address[:80], error_message)
            return GoogleValidationResult(success=False, error=error_message)

        return cls._parse_response(data)

    @classmethod
    def _parse_response(cls, data: dict) -> GoogleValidationResult:
        """Parse the raw OpenCage response into a structured result."""
        results = data.get("results") or []
        if not results:
            # OSM coverage in PK is patchy — a missing hit means "couldn't
            # confirm", not necessarily "fake". Leave it unverified.
            return GoogleValidationResult(
                verdict="UNRESOLVED",
                status="unverified",
                confidence_score=0.0,
                raw_response=data,
                success=True,
            )

        top = results[0]
        components = top.get("components", {})
        geometry = top.get("geometry", {})
        confidence = int(top.get("confidence") or 0)
        component_type = str(components.get("_type") or "").lower()

        # ── Structured components ────────────────────────────────────
        city = (
            components.get("city")
            or components.get("town")
            or components.get("village")
            or components.get("municipality")
            or ""
        )
        province = components.get("state") or components.get("province") or ""
        postal_code = components.get("postcode") or ""
        country_code = (components.get("country_code") or "").upper()
        district = (
            components.get("suburb")
            or components.get("city_district")
            or components.get("county")
            or components.get("neighbourhood")
            or ""
        )

        # ── Precision / granularity (drives validity) ────────────────
        has_premise = component_type in _PREMISE_TYPES or bool(components.get("house_number"))
        has_street = component_type in _STREET_TYPES or bool(components.get("road"))
        if has_premise:
            granularity, geocode_granularity = "PREMISE", "rooftop"
            verdict, status = "CONFIRMED", "valid"
        elif has_street:
            granularity, geocode_granularity = "ROUTE", "range_interpolated"
            # A precise street hit is deliverable; a fuzzy one is plausible.
            if confidence >= _CONFIDENCE_STREET_VALID:
                verdict, status = "CONFIRMED", "valid"
            else:
                verdict, status = "UNCONFIRMED_BUT_PLAUSIBLE", "partial"
        elif city:
            # Area resolved but no street/premise — confirmed locality only.
            granularity, geocode_granularity = "BLOCK", ""
            verdict, status = "UNCONFIRMED_BUT_PLAUSIBLE", "partial"
        else:
            # Resolved no finer than province/country — effectively unmatched.
            granularity, geocode_granularity = "OTHER", ""
            verdict, status = "UNCONFIRMED_AND_SUSPICIOUS", "mismatch"

        confidence_score = _GRANULARITY_SCORE.get(granularity, 30.0)

        return GoogleValidationResult(
            verdict=verdict,
            validation_granularity=granularity,
            geocode_granularity=geocode_granularity,
            address_complete=bool(city and country_code),
            formatted_address=top.get("formatted", ""),
            city=city,
            province=province,
            postal_code=postal_code,
            country_code=country_code,
            district=district,
            latitude=geometry.get("lat"),
            longitude=geometry.get("lng"),
            confidence_score=confidence_score,
            status=status,
            raw_response=data,
            success=True,
        )


def _request_error_message(exc: requests.exceptions.RequestException) -> str:
    """Return an actionable OpenCage error without leaking the API key."""
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    api_message = ""

    if response is not None:
        try:
            payload = response.json()
            api_message = payload.get("status", {}).get("message", "")
        except ValueError:
            api_message = ""

    if status_code == 401:
        return "OpenCage API returned 401: invalid or missing OPENCAGE_API_KEY."
    if status_code == 402:
        return "OpenCage API returned 402: daily free-tier quota exhausted."
    if status_code == 403:
        return "OpenCage API returned 403: key disabled or IP/referrer blocked."
    if status_code:
        message = f"OpenCage API returned HTTP {status_code}."
        if api_message:
            message = f"{message} {api_message}"
        return message

    return f"OpenCage API request failed: {exc.__class__.__name__}"

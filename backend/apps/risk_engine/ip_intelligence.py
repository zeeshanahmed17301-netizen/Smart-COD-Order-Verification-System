"""External IP intelligence providers used by order enrichment."""

from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


DEFAULT_TIMEOUT_SECONDS = 4.0


@dataclass
class IPIntelligenceResult:
    """Normalized IP intelligence payload for enrichment."""

    provider: str
    risk_score: float
    city: str
    region: str
    country: str
    is_anonymous: bool
    is_anonymous_vpn: bool
    is_public_proxy: bool
    is_residential_proxy: bool
    is_tor_exit_node: bool
    is_hosting_provider: bool
    geo_matches_shipping_city: bool | None
    geo_matches_shipping_country: bool | None


def _empty_result(provider: str = "internal_observed") -> IPIntelligenceResult:
    return IPIntelligenceResult(
        provider=provider,
        risk_score=0.0,
        city="",
        region="",
        country="",
        is_anonymous=False,
        is_anonymous_vpn=False,
        is_public_proxy=False,
        is_residential_proxy=False,
        is_tor_exit_node=False,
        is_hosting_provider=False,
        geo_matches_shipping_city=None,
        geo_matches_shipping_country=None,
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _matches_location(candidate: str | None, *expected_values: str | None) -> bool | None:
    normalized_candidate = (candidate or "").strip().casefold()
    normalized_expected = {
        str(value).strip().casefold()
        for value in expected_values
        if str(value or "").strip()
    }
    if not normalized_expected:
        return None
    return normalized_candidate in normalized_expected


class IPIntelligenceService:
    """Resolve IP geolocation and fraud attributes from a configured provider."""

    @classmethod
    def evaluate(
        cls,
        *,
        ip_address: str,
        shipping_city: str | None = None,
        shipping_country: str | None = None,
    ) -> IPIntelligenceResult:
        provider = str(
            getattr(settings, "IP_INTELLIGENCE_PROVIDER", "internal_observed")
        ).strip().lower()

        if provider == "ipqualityscore":
            return cls._from_ipqualityscore(
                ip_address=ip_address,
                shipping_city=shipping_city,
                shipping_country=shipping_country,
            )
        if provider == "ipapi":
            return cls._from_ipapi(
                ip_address=ip_address,
                shipping_city=shipping_city,
                shipping_country=shipping_country,
            )
        if provider == "ipapicom":
            return cls._from_ipapicom(
                ip_address=ip_address,
                shipping_city=shipping_city,
                shipping_country=shipping_country,
            )
        return _empty_result(provider="internal_observed")

    @classmethod
    def _from_ipqualityscore(
        cls,
        *,
        ip_address: str,
        shipping_city: str | None,
        shipping_country: str | None,
    ) -> IPIntelligenceResult:
        api_key = getattr(settings, "IPQUALITYSCORE_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "IPQualityScore is configured, but IPQUALITYSCORE_API_KEY is missing."
            )

        timeout = _safe_float(
            getattr(settings, "IP_INTELLIGENCE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
            DEFAULT_TIMEOUT_SECONDS,
        )
        url = f"https://ipqualityscore.com/api/json/ip/{api_key}/{ip_address}"

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return _empty_result(provider="ipqualityscore")

        country = payload.get("country_code") or payload.get("country") or ""
        return IPIntelligenceResult(
            provider="ipqualityscore",
            risk_score=round(min(max(_safe_float(payload.get("fraud_score")), 0.0), 100.0), 1),
            city=str(payload.get("city") or ""),
            region=str(payload.get("region") or ""),
            country=str(country),
            is_anonymous=_safe_bool(payload.get("vpn")) or _safe_bool(payload.get("tor")),
            is_anonymous_vpn=_safe_bool(payload.get("vpn")) or _safe_bool(payload.get("active_vpn")),
            is_public_proxy=_safe_bool(payload.get("proxy")),
            is_residential_proxy=False,
            is_tor_exit_node=_safe_bool(payload.get("tor")),
            is_hosting_provider=str(payload.get("connection_type") or "").strip().casefold()
            in {"hosting", "data center/web hosting/transit", "corporate"},
            geo_matches_shipping_city=_matches_location(
                payload.get("city"),
                shipping_city,
            ),
            geo_matches_shipping_country=_matches_location(
                country,
                shipping_country,
            ),
        )

    @classmethod
    def _from_ipapi(
        cls,
        *,
        ip_address: str,
        shipping_city: str | None,
        shipping_country: str | None,
    ) -> IPIntelligenceResult:
        timeout = _safe_float(
            getattr(settings, "IP_INTELLIGENCE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
            DEFAULT_TIMEOUT_SECONDS,
        )
        try:
            response = requests.get(
                f"https://ipapi.co/{ip_address}/json/",
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return _empty_result(provider="ipapi")

        country_code = payload.get("country") or payload.get("country_code") or ""
        country_name = payload.get("country_name") or ""
        return IPIntelligenceResult(
            provider="ipapi",
            risk_score=0.0,
            city=str(payload.get("city") or ""),
            region=str(payload.get("region") or ""),
            country=str(country_name or country_code),
            is_anonymous=False,
            is_anonymous_vpn=False,
            is_public_proxy=False,
            is_residential_proxy=False,
            is_tor_exit_node=False,
            is_hosting_provider=False,
            geo_matches_shipping_city=_matches_location(
                payload.get("city"),
                shipping_city,
            ),
            geo_matches_shipping_country=_matches_location(
                country_code or country_name,
                shipping_country,
                country_name,
            ),
        )

    @classmethod
    def _from_ipapicom(
        cls,
        *,
        ip_address: str,
        shipping_city: str | None,
        shipping_country: str | None,
    ) -> IPIntelligenceResult:
        """Use ip-api.com (free, 45 req/min, no key required, HTTP only)."""
        timeout = _safe_float(
            getattr(settings, "IP_INTELLIGENCE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
            DEFAULT_TIMEOUT_SECONDS,
        )
        fields = "status,city,regionName,country,countryCode,query"
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip_address}?fields={fields}",
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return _empty_result(provider="ipapicom")

        if payload.get("status") != "success":
            return _empty_result(provider="ipapicom")

        country_code = payload.get("countryCode") or ""
        country_name = payload.get("country") or ""
        city = str(payload.get("city") or "")
        return IPIntelligenceResult(
            provider="ipapicom",
            risk_score=0.0,
            city=city,
            region=str(payload.get("regionName") or ""),
            country=str(country_name or country_code),
            is_anonymous=False,
            is_anonymous_vpn=False,
            is_public_proxy=False,
            is_residential_proxy=False,
            is_tor_exit_node=False,
            is_hosting_provider=False,
            geo_matches_shipping_city=_matches_location(city, shipping_city),
            geo_matches_shipping_country=_matches_location(
                country_code or country_name,
                shipping_country,
                country_name,
            ),
        )

"""Courier branch reachability service.

Checks whether major courier services (Leopard, TCS, etc.) have branches
that can reach a given delivery address by fuzzy-matching city names against
the ``CourierBranch`` table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from django.db.models import QuerySet


# ---------------------------------------------------------------------------
# City normalization
# ---------------------------------------------------------------------------

# Common Pakistani city aliases / abbreviations → canonical name
_CITY_ALIASES: dict[str, str] = {
    "isb": "islamabad",
    "isl": "islamabad",
    "rwp": "rawalpindi",
    "pindi": "rawalpindi",
    "lhr": "lahore",
    "khi": "karachi",
    "kci": "karachi",
    "fsd": "faisalabad",
    "lyp": "faisalabad",
    "mux": "multan",
    "mtn": "multan",
    "pew": "peshawar",
    "psh": "peshawar",
    "guj": "gujranwala",
    "gwl": "gujranwala",
    "skt": "sialkot",
    "dgk": "dera ghazi khan",
    "d.g. khan": "dera ghazi khan",
    "d.g.khan": "dera ghazi khan",
    "dg khan": "dera ghazi khan",
    "d.i. khan": "dera ismail khan",
    "d.i.khan": "dera ismail khan",
    "di khan": "dera ismail khan",
    "dik": "dera ismail khan",
    "bwp": "bahawalpur",
    "bwn": "bahawalnagar",
    "sag": "sargodha",
    "mbd": "mandi bahauddin",
    "abb": "abbottabad",
    "abbotabad": "abbottabad",
    "abottabad": "abbottabad",
    "mrdn": "mardan",
    "swt": "swat",
    "hyd": "hyderabad",
    "ryd": "rahim yar khan",
    "ryk": "rahim yar khan",
    "skr": "sukkur",
    "qta": "quetta",
    "sahiwal": "sahiwal",
    "okara": "okara",
    "jhang": "jhang",
    "a.k": "azad kashmir",
    "a.k.": "azad kashmir",
    "ak": "azad kashmir",
    "mirpur ak": "mirpur",
    "muzaffarabad": "muzaffarabad",
    "wah cantt": "wah cantt",
    "wah": "wah cantt",
    "taxila": "taxila",
}

_NON_CITY_LOCATION_NAMES = {
    "pakistan",
    "punjab",
    "sindh",
    "khyber pakhtunkhwa",
    "kpk",
    "balochistan",
    "baluchistan",
    "gilgit baltistan",
    "gb",
    "azad jammu kashmir",
    "ajk",
    "azad kashmir",
    "islamabad capital territory",
    "ict",
}


def normalize_city(raw: str) -> str:
    """Return a lowered, trimmed, alias-resolved city name."""
    cleaned = re.sub(r"[^a-z0-9\s]", "", (raw or "").lower().strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _CITY_ALIASES.get(cleaned, cleaned)


def _is_indexable_city(value: str) -> bool:
    normalized = normalize_city(value)
    if not normalized or normalized in _NON_CITY_LOCATION_NAMES:
        return False
    tokens = normalized.split()
    return bool(tokens) and not all(token in _NON_CITY_LOCATION_NAMES for token in tokens)


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase alphanumeric tokens."""
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) > 2}


# ---------------------------------------------------------------------------
# Branch → city extraction
# ---------------------------------------------------------------------------

# Tokens to strip when extracting city from a branch name
_BRAND_TOKENS = {
    "leopard", "courier", "service", "tcs", "postex",
    "branch", "express", "center", "centre", "franchise",
}


def extract_city_from_branch_name(branch_name: str) -> str:
    """Extract the city/area portion from a branch name string.

    Examples:
        "Leopard Courier Service ARIFWALA BRANCH" → "arifwala"
        "TCS Courier Allama Iqbal Town Branch Lahore" → "lahore"
        "TCS Courier Lane 5 Peshawar Road RWP" → "rwp"
    """
    tokens = re.split(r"[\s,\-]+", (branch_name or "").strip())
    meaningful = [
        t.lower()
        for t in tokens
        if t.lower() not in _BRAND_TOKENS and len(t) > 1
    ]
    # The last meaningful token is usually the city
    if meaningful:
        candidate = meaningful[-1]
        return normalize_city(candidate)
    return ""


def extract_city_from_address(address: str) -> str:
    """Extract the likely city from a free-text branch address.

    Heuristic: the last comma-delimited segment (ignoring trailing periods)
    often contains the city name.
    """
    parts = [p.strip().rstrip(".") for p in (address or "").split(",") if p.strip()]
    if parts:
        return normalize_city(parts[-1])
    return normalize_city(address)


# ---------------------------------------------------------------------------
# Reachability result
# ---------------------------------------------------------------------------

@dataclass
class CourierReachabilityResult:
    """Result of checking whether courier services cover a delivery area."""

    is_reachable: bool = False
    reachable_couriers: list[str] = field(default_factory=list)
    nearest_branches: list[dict] = field(default_factory=list)
    match_confidence: str = "none"  # exact | fuzzy | city_level | none
    coverage_score: float = 0.0     # 0-100

    def to_dict(self) -> dict:
        return {
            "is_reachable": self.is_reachable,
            "reachable_couriers": self.reachable_couriers,
            "nearest_branches": self.nearest_branches,
            "match_confidence": self.match_confidence,
            "coverage_score": self.coverage_score,
        }


# ---------------------------------------------------------------------------
# Coverage index (in-memory cache built from DB)
# ---------------------------------------------------------------------------

class _CoverageIndex:
    """In-memory index mapping normalized city → set of brands & branches."""

    def __init__(self) -> None:
        self._city_to_brands: dict[str, set[str]] = {}
        self._city_to_branches: dict[str, list[dict]] = {}
        self._all_cities: set[str] = set()
        self._total_brands: int = 0
        self._loaded = False

    def load(self, *, force: bool = False) -> None:
        """Populate from the CourierBranch DB table."""
        if self._loaded and not force:
            return

        from apps.addresses.models import CourierBranch

        self._city_to_brands.clear()
        self._city_to_branches.clear()

        branches: QuerySet = CourierBranch.objects.filter(
            is_active=True,
        ).values("brand", "branch_name", "address", "phone", "city_normalized")

        brand_set: set[str] = set()
        for branch in branches:
            brand = branch["brand"]
            brand_set.add(brand)
            city = normalize_city(branch["city_normalized"])
            if not _is_indexable_city(city):
                continue

            self._city_to_brands.setdefault(city, set()).add(brand)
            self._city_to_branches.setdefault(city, []).append({
                "brand": brand,
                "branch_name": branch["branch_name"],
                "address": branch["address"],
                "phone": branch["phone"],
            })

        self._all_cities = set(self._city_to_brands.keys())
        self._total_brands = len(brand_set) or 1
        self._loaded = True

    @property
    def total_brands(self) -> int:
        self.load()
        return self._total_brands

    def exact_match(self, city: str) -> tuple[set[str], list[dict]]:
        self.load()
        if not _is_indexable_city(city):
            return set(), []
        brands = self._city_to_brands.get(city, set())
        branches = self._city_to_branches.get(city, [])
        return brands, branches

    def fuzzy_match(self, city: str, threshold: float = 0.80) -> tuple[set[str], list[dict], str]:
        """Find the best fuzzy match among indexed cities."""
        self.load()
        if not _is_indexable_city(city):
            return set(), [], ""
        best_ratio = 0.0
        best_city = ""
        for indexed_city in self._all_cities:
            ratio = SequenceMatcher(None, city, indexed_city).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_city = indexed_city

        if best_ratio >= threshold and best_city:
            brands = self._city_to_brands.get(best_city, set())
            branches = self._city_to_branches.get(best_city, [])
            return brands, branches, best_city
        return set(), [], ""

    def address_token_match(self, address_tokens: set[str]) -> tuple[set[str], list[dict], str]:
        """Check if any indexed city name appears as a token in the address."""
        self.load()
        for indexed_city in self._all_cities:
            if not _is_indexable_city(indexed_city):
                continue
            city_tokens = _tokenize(indexed_city)
            if city_tokens and city_tokens.issubset(address_tokens):
                brands = self._city_to_brands.get(indexed_city, set())
                branches = self._city_to_branches.get(indexed_city, [])
                return brands, branches, indexed_city
        return set(), [], ""

    def invalidate(self) -> None:
        """Force a reload on next access (call after importing new branches)."""
        self._loaded = False


# Module-level singleton
_coverage_index = _CoverageIndex()


def invalidate_coverage_cache() -> None:
    """Force the coverage index to reload from the database."""
    _coverage_index.invalidate()


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def check_reachability(city: str, address: str = "") -> CourierReachabilityResult:
    """Check whether major courier services can reach a delivery location.

    Matching strategy (ordered by confidence):
    1. Exact normalized city match
    2. Fuzzy city match (Levenshtein ratio > 0.80)
    3. Address token match (city name found inside the full address string)
    4. No match → unreachable
    """
    normalized = normalize_city(city)
    address_tokens = _tokenize(address)

    # 1️⃣ Exact match
    brands, branches = _coverage_index.exact_match(normalized)
    if brands:
        return _build_result(brands, branches, "exact")

    # 2️⃣ Fuzzy match
    brands, branches, _ = _coverage_index.fuzzy_match(normalized)
    if brands:
        return _build_result(brands, branches, "fuzzy")

    # 3️⃣ Address token match
    if address_tokens:
        brands, branches, _ = _coverage_index.address_token_match(address_tokens)
        if brands:
            return _build_result(brands, branches, "city_level")

    # 4️⃣ No match
    return CourierReachabilityResult(
        is_reachable=False,
        reachable_couriers=[],
        nearest_branches=[],
        match_confidence="none",
        coverage_score=0.0,
    )


def _build_result(
    brands: set[str],
    branches: list[dict],
    confidence: str,
) -> CourierReachabilityResult:
    total = _coverage_index.total_brands
    coverage = round((len(brands) / total) * 100, 1) if total else 0.0
    return CourierReachabilityResult(
        is_reachable=True,
        reachable_couriers=sorted(brands),
        nearest_branches=branches[:3],
        match_confidence=confidence,
        coverage_score=coverage,
    )

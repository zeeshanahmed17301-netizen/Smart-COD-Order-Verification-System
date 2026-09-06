"""Address validation rules based on structure and keywords."""

from __future__ import annotations

import re


# Deliverable-reference keywords. The original new-requirenment.md set assumed
# every real address contains a Western-style "Street/Road/Block". In practice a
# large share of genuine Pakistani addresses are located by locality or landmark
# instead (e.g. "Maira Ilaqa", "Saddar Bazar", "COMSATS University ... Campus",
# "Chawni Mahal"). Penalising those as "no keyword" is a false positive, so the
# vocabulary is widened to the locality + landmark terms real orders actually use.
# Matching is whole-word (see below), and genuine junk ("sdfsdcfsd", bare city
# names, "test address abc area") still has none of these, so the signal holds.
VALID_KEYWORDS = {
    # — structure / locality —
    "street",
    "road",
    "mohalla",
    "mohallah",
    "muhalla",
    "colony",
    "sector",
    "phase",
    "town",
    "block",
    "chowk",
    "near",
    "gali",
    "kucha",
    "ilaqa",
    "mahal",
    "chawni",
    "cantt",
    "nagar",
    "pura",
    "gulshan",
    "gulberg",
    "scheme",
    "society",
    "saddar",
    "bazaar",
    "bazar",
    "market",
    "ganj",
    "gunj",
    "abadi",
    "basti",
    # — landmarks (locate a delivery point on their own) —
    "university",
    "college",
    "campus",
    "school",
    "hospital",
    "clinic",
    "plaza",
    "mall",
    "tower",
    "adda",
    "morr",
    "gate",
    "park",
    "stand",
    "stop",
    "stadium",
    "airport",
    "station",
}

BLACKLIST_WORDS = {"abc", "xyz", "test", "fake", "shetan"}
VAGUE_PATTERNS = {
    "near market",
    "street only",
    "same as before",
    "call me",
    "near masjid",
}


def validate_address(full_address: str | None, city: str | None, district: str | None = "") -> dict:
    full_text = (full_address or "").strip()
    city_text = (city or "").strip()
    district_text = (district or "").strip()
    lowered = full_text.casefold()
    # Whole-word tokens so single-word keyword/blacklist checks match on word
    # boundaries — "test" must not fire inside "greatest", nor "abc" inside a
    # longer word. Multi-word vague phrases are still matched as substrings.
    tokens = set(re.findall(r"[a-z]+", lowered))

    flags: list[str] = []
    score_delta = 0

    has_keyword = bool(tokens & VALID_KEYWORDS)
    has_blacklist_word = bool(tokens & BLACKLIST_WORDS)
    is_vague = any(pattern in lowered for pattern in VAGUE_PATTERNS)
    has_min_length = len(full_text) >= 10
    has_city = bool(city_text)
    has_detail = has_keyword or len(district_text) >= 3 or "," in full_text
    is_structured = has_min_length and has_city and has_detail

    if is_structured and has_keyword:
        score_delta += 2
    else:
        score_delta -= 2

    if not has_min_length:
        flags.append("too_short")
    if not has_city:
        flags.append("missing_city")
    if not has_keyword:
        flags.append("missing_keyword")
    if is_vague:
        flags.append("vague")
    if has_blacklist_word:
        flags.append("blacklist_word")

    return {
        "score_delta": score_delta,
        "is_structured": is_structured,
        "has_keyword": has_keyword,
        "is_vague": is_vague,
        "has_blacklist_word": has_blacklist_word,
        "flags": flags,
    }
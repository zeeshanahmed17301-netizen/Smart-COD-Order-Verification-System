"""Customer name validation rules."""

from __future__ import annotations

import re


COMMON_PAKISTANI_NAMES = {
    "ali",
    "ahmed",
    "ayesha",
    "fatima",
    "hassan",
    "hussain",
    "muhammad",
    "mohammad",
    "usman",
    "umar",
    "bilal",
    "zainab",
    "maryam",
    "mariam",
    "sara",
    "sarah",
    "amna",
    "zara",
    "hamza",
}

SUSPICIOUS_NAME_TOKENS = {"abc", "xyz", "test", "fake", "user"}


def _looks_repetitive(text: str) -> bool:
    cleaned = re.sub(r"[^a-z]", "", text.lower())
    if len(cleaned) < 3:
        return True
    if len(set(cleaned)) <= 2 and len(cleaned) >= 4:
        return True
    return bool(re.fullmatch(r"([a-z])\1{3,}", cleaned))


def validate_name(value: str | None) -> dict:
    raw_name = (value or "").strip()
    lowered = raw_name.casefold()
    tokens = [token for token in re.split(r"\s+", lowered) if token]

    flags: list[str] = []
    score_delta = 0

    if len(raw_name) < 3:
        flags.append("too_short")
    if any(ch.isdigit() for ch in raw_name):
        flags.append("contains_digits")
    if lowered in SUSPICIOUS_NAME_TOKENS or _looks_repetitive(raw_name):
        flags.append("suspicious_pattern")

    if flags:
        score_delta = -2

    is_common_name = any(token in COMMON_PAKISTANI_NAMES for token in tokens)

    return {
        "score_delta": score_delta,
        "is_common_name": is_common_name,
        "is_suspicious": bool(flags),
        "flags": flags,
    }
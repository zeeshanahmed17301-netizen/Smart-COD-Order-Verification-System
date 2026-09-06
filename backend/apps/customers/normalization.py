"""Customer identity normalization helpers."""

from __future__ import annotations

import re


def normalize_phone(value: str | None) -> str:
    """Return a stable phone identity, preferring E.164-like Pakistan numbers."""
    raw = (value or "").strip()
    if not raw:
        return ""

    compact = re.sub(r"[^\d+]", "", raw)
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"

    if compact.startswith("+"):
        digits = compact[1:]
        if digits.startswith("92") and len(digits) == 12:
            return f"+{digits}"
        return compact

    digits = re.sub(r"\D", "", compact)
    if not digits:
        return ""

    if digits.startswith("92") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("03") and len(digits) == 11:
        return f"+92{digits[1:]}"
    if digits.startswith("3") and len(digits) == 10:
        return f"+92{digits}"

    return digits

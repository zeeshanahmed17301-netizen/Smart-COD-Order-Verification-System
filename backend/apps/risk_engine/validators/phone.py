"""Phone validation rules for COD order scoring."""

from __future__ import annotations


def _to_local_phone(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("92") and len(digits) == 12:
        return f"0{digits[2:]}"
    if digits.startswith("3") and len(digits) == 10:
        return f"0{digits}"
    return digits


def _has_long_repeat(phone: str, threshold: int = 7) -> bool:
    current = 0
    last = ""
    for digit in phone:
        if digit == last:
            current += 1
        else:
            current = 1
            last = digit
        if current >= threshold:
            return True
    return False


def _has_sequence(phone: str, length: int = 6) -> bool:
    for start in range(0, max(len(phone) - length + 1, 0)):
        chunk = phone[start : start + length]
        asc = True
        desc = True
        for index in range(1, len(chunk)):
            prev_digit = int(chunk[index - 1])
            current_digit = int(chunk[index])
            if current_digit != prev_digit + 1:
                asc = False
            if current_digit != prev_digit - 1:
                desc = False
        if asc or desc:
            return True
    return False


def validate_phone(value: str | None, *, prior_order_count: int = 0) -> dict:
    phone = _to_local_phone(value)
    flags: list[str] = []
    score_delta = 0

    if len(phone) != 11 or not phone.startswith("03"):
        flags.append("invalid_format")
        score_delta -= 2
    else:
        score_delta += 2

    if _has_long_repeat(phone):
        flags.append("repeated_digits")
    if _has_sequence(phone):
        flags.append("sequential_digits")

    if "repeated_digits" in flags or "sequential_digits" in flags:
        if score_delta > 0:
            score_delta -= 2
        elif score_delta == 0:
            score_delta = -2

    if prior_order_count > 3:
        flags.append("repeat_customer_phone")

    return {
        "normalized": phone,
        "score_delta": score_delta,
        "valid": score_delta > 0 and not {"repeated_digits", "sequential_digits"}.intersection(flags),
        "is_suspicious": bool({"invalid_format", "repeated_digits", "sequential_digits"}.intersection(flags)),
        "repeat_customer": prior_order_count > 3,
        "flags": flags,
    }
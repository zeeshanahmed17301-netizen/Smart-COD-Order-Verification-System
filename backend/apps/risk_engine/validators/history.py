"""Order history validation rules."""

from __future__ import annotations


def validate_order_history(*, total_orders: int = 0, delivered_count: int = 0, rto_count: int = 0) -> dict:
    score_delta = 0
    flags: list[str] = []

    if rto_count > 0:
        score_delta -= 3
        flags.append("previous_rto")

    if delivered_count > 0:
        score_delta += 2
        flags.append("successful_deliveries")
    elif total_orders <= 1:
        flags.append("first_order")

    return {
        "score_delta": score_delta,
        "has_previous_rto": rto_count > 0,
        "has_successful_deliveries": delivered_count > 0,
        "is_first_order": total_orders <= 1,
        "flags": flags,
    }
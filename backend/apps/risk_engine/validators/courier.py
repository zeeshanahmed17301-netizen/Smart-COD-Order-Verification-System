"""Courier reachability rule helpers."""

from __future__ import annotations


def validate_courier(*, reachable: bool | None, coverage_score: float = 0.0) -> dict:
    if reachable is True:
        return {
            "score_delta": 2,
            "is_available": True,
            "coverage_score": float(coverage_score or 100.0),
            "flags": [],
        }

    if reachable is False:
        return {
            "score_delta": -2,
            "is_available": False,
            "coverage_score": float(coverage_score or 0.0),
            "flags": ["unserviceable"],
        }

    return {
        "score_delta": 0,
        "is_available": None,
        "coverage_score": float(coverage_score or 0.0),
        "flags": ["unknown"],
    }
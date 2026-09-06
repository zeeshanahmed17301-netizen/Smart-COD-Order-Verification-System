"""Fit and serve isotonic score→probability calibrations.

Fitting happens offline (the ``evaluate_risk_engine --fit`` command); serving
happens online inside the scorer via ``ScoreCalibrationService``. A fitted model
turns a raw 0-100 score into a probability whose meaning is backed by observed
outcomes — e.g. "orders scoring ~70 actually RTO'd 68% of the time".
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.risk_engine.metrics import IsotonicBin, fit_isotonic, wilson_interval
from apps.risk_engine.models import RiskCalibrationModel


@dataclass
class ServedProbability:
    probability: float          # 0-100
    confidence_low: float       # 0-100
    confidence_high: float      # 0-100
    sample_size: int
    score_range: tuple[float, float]
    source: str                 # "isotonic" when fitted, "uncalibrated" otherwise
    is_estimated: bool
    version: str


def fit_and_activate(
    *,
    target: str,
    scores: list[float],
    labels: list[int],
    version: str,
    label_definition: str = "",
    auc: float | None = None,
    ece: float | None = None,
    notes: str = "",
) -> RiskCalibrationModel:
    """Fit an isotonic calibration for ``target`` and make it the active one."""
    bins = fit_isotonic(scores, labels)
    payload = [
        {
            "score_lo": b.score_lo,
            "score_hi": b.score_hi,
            "probability": b.probability,
            "count": b.count,
            "positives": b.positives,
        }
        for b in bins
    ]
    with transaction.atomic():
        RiskCalibrationModel.objects.filter(target=target, is_active=True).update(
            is_active=False
        )
        model = RiskCalibrationModel.objects.create(
            target=target,
            version=version,
            method="isotonic",
            bins=payload,
            sample_size=len(scores),
            positives=sum(1 for y in labels if y == 1),
            auc=auc,
            ece=ece,
            label_definition=label_definition[:255],
            is_active=True,
            notes=notes,
        )
    return model


def _active_model(target: str) -> RiskCalibrationModel | None:
    return (
        RiskCalibrationModel.objects.filter(target=target, is_active=True)
        .order_by("-trained_at")
        .first()
    )


def _bin_for_score(bins: list[dict], score: float) -> dict | None:
    for b in bins:
        if b["score_lo"] <= score <= b["score_hi"]:
            return b
    return bins[-1] if bins else None


def serve(target: str, score: float, *, default_version: str) -> ServedProbability:
    """Map a raw score to a calibrated probability using the active model.

    Falls back to an explicitly-flagged ``uncalibrated`` pass-through (probability
    == score) when no model has been fitted yet — honest about the fact that the
    number is not yet outcome-backed, instead of pretending it is.
    """
    score = max(0.0, min(float(score or 0.0), 100.0))
    model = _active_model(target)

    if model and model.bins:
        b = _bin_for_score(model.bins, score)
        if b is not None:
            probability = b["probability"] * 100.0
            low, high = wilson_interval(int(b["positives"]), int(b["count"]))
            return ServedProbability(
                probability=round(probability, 1),
                confidence_low=round(low * 100.0, 1),
                confidence_high=round(high * 100.0, 1),
                sample_size=int(b["count"]),
                score_range=(float(b["score_lo"]), float(b["score_hi"])),
                source="isotonic",
                is_estimated=False,
                version=model.version,
            )

    # No fitted model → honest pass-through, clearly flagged as estimated.
    interval = 8.0 if score >= 50 else 6.0
    return ServedProbability(
        probability=round(score, 1),
        confidence_low=max(0.0, round(score - interval, 1)),
        confidence_high=min(100.0, round(score + interval, 1)),
        sample_size=0,
        score_range=(max(0.0, score - 5.0), min(100.0, score + 5.0)),
        source="uncalibrated",
        is_estimated=True,
        version=default_version,
    )

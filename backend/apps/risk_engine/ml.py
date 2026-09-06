"""Dependency-free logistic-regression challenger for RTO prediction.

No numpy/sklearn — standardisation + batch gradient descent in pure Python, so it
runs anywhere the app runs and stays fully inspectable (every coefficient is a
plain number you can read). The model is deliberately simple and linear: it is a
*challenger* to the rules, not a black box. The rules remain the champion and the
hard guardrails (blacklist, fake-address words) always apply on top.

Feature encoding is derived from the Track-2 feature contract so the model can
only ever consume features the engine actually captures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from apps.risk_engine.features import FEATURE_NAMES

# String categoricals are excluded from the linear model (kept human-readable in
# the snapshot, but not one-hot encoded here to keep the challenger simple).
_EXCLUDED = {"chat_status", "shopify_recommendation", "shopify_risk_level"}
# Tri-state features whose "unknown" (None) is imputed to a neutral 0.5.
_TRISTATE = {"courier_available", "ip_geo_matches_shipping_city"}

ML_FEATURE_ORDER: list[str] = [f for f in FEATURE_NAMES if f not in _EXCLUDED]


def _sigmoid(z: float) -> float:
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def encode(features: dict, feature_order: list[str] | None = None) -> list[float]:
    """Turn a feature dict into a numeric vector in a fixed order."""
    order = feature_order or ML_FEATURE_ORDER
    row: list[float] = []
    for name in order:
        value = features.get(name)
        if value is None:
            row.append(0.5 if name in _TRISTATE else 0.0)
        else:
            row.append(float(value))
    return row


@dataclass
class LogisticModel:
    feature_order: list[str]
    means: list[float]
    stds: list[float]
    weights: list[float]
    bias: float

    def predict_proba(self, features: dict) -> float:
        row = encode(features, self.feature_order)
        z = self.bias
        for value, mean, std, weight in zip(row, self.means, self.stds, self.weights):
            z += weight * ((value - mean) / std if std > 1e-12 else 0.0)
        return _sigmoid(z)

    def to_dict(self) -> dict:
        return {
            "feature_order": self.feature_order,
            "means": self.means,
            "stds": self.stds,
            "weights": self.weights,
            "bias": self.bias,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogisticModel":
        return cls(
            feature_order=list(data["feature_order"]),
            means=list(data["means"]),
            stds=list(data["stds"]),
            weights=list(data["weights"]),
            bias=float(data["bias"]),
        )


def _standardise(rows: list[list[float]]) -> tuple[list[float], list[float]]:
    n = len(rows)
    d = len(rows[0])
    means = [sum(r[j] for r in rows) / n for j in range(d)]
    stds = []
    for j in range(d):
        var = sum((r[j] - means[j]) ** 2 for r in rows) / n
        stds.append(math.sqrt(var))
    return means, stds


def fit_logistic(
    feature_dicts: list[dict],
    labels: list[int],
    *,
    feature_order: list[str] | None = None,
    epochs: int = 400,
    lr: float = 0.3,
    l2: float = 1e-3,
) -> LogisticModel:
    """Fit L2-regularised logistic regression via batch gradient descent."""
    order = feature_order or ML_FEATURE_ORDER
    rows = [encode(f, order) for f in feature_dicts]
    if not rows:
        raise ValueError("no training rows")
    means, stds = _standardise(rows)

    # Standardise once up front.
    std_rows = [
        [((r[j] - means[j]) / stds[j] if stds[j] > 1e-12 else 0.0) for j in range(len(order))]
        for r in rows
    ]

    n = len(std_rows)
    d = len(order)
    weights = [0.0] * d
    bias = 0.0

    for _ in range(epochs):
        grad_w = [0.0] * d
        grad_b = 0.0
        for row, y in zip(std_rows, labels):
            z = bias + sum(weights[j] * row[j] for j in range(d))
            error = _sigmoid(z) - y
            grad_b += error
            for j in range(d):
                grad_w[j] += error * row[j]
        bias -= lr * grad_b / n
        for j in range(d):
            weights[j] -= lr * (grad_w[j] / n + l2 * weights[j])

    return LogisticModel(
        feature_order=order, means=means, stds=stds, weights=weights, bias=bias
    )


@dataclass
class MLPrediction:
    probability: float    # 0-1
    version: str
    role: str             # "shadow" | "challenger" | "champion"


class MLChallenger:
    """Serve the active RTO model. Returns None when none is active."""

    @staticmethod
    def predict(target: str, features: dict) -> MLPrediction | None:
        from apps.risk_engine.models import RiskMLModel

        record = (
            RiskMLModel.objects.filter(target=target, is_active=True)
            .order_by("-trained_at")
            .first()
        )
        if record is None or not record.params:
            return None
        try:
            model = LogisticModel.from_dict(record.params)
            probability = model.predict_proba(features)
        except Exception:
            return None
        return MLPrediction(
            probability=probability, version=record.version, role=record.role
        )

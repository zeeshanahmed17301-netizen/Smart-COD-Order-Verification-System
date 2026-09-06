"""Dependency-free evaluation + calibration math for the risk engine.

Everything here is pure Python (no numpy/sklearn) so it runs anywhere the
Django app runs. It powers two things:

* the ``evaluate_risk_engine`` backtest (does a score actually predict the
  outcome?), and
* isotonic score→probability calibration (turn a raw 0-100 score into a real
  probability backed by observed outcomes).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def roc_auc(labels: list[int], scores: list[float]) -> float | None:
    """Area under the ROC curve via the rank-sum (Mann–Whitney U) identity.

    Handles tied scores with average ranks. Returns ``None`` when one class is
    absent (AUC is undefined without both positives and negatives).
    """
    if len(labels) != len(scores):
        raise ValueError("labels and scores must be the same length")
    n_pos = sum(1 for y in labels if y == 1)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None

    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        # Average rank (1-based) for the tie group [i, j].
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1

    sum_pos_ranks = sum(ranks[i] for i in range(len(labels)) if labels[i] == 1)
    auc = (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return round(auc, 4)


@dataclass
class ThresholdRow:
    threshold: float
    flagged: int
    true_positive: int
    false_positive: int
    precision: float
    recall: float          # a.k.a. catch rate / TPR
    false_positive_rate: float


def precision_recall_table(
    labels: list[int], scores: list[float], thresholds: list[float]
) -> list[ThresholdRow]:
    """Confusion-derived precision/recall/FPR at each ``score >= threshold``."""
    total_pos = sum(1 for y in labels if y == 1)
    total_neg = len(labels) - total_pos
    rows: list[ThresholdRow] = []
    for threshold in thresholds:
        tp = fp = 0
        for label, score in zip(labels, scores):
            if score >= threshold:
                if label == 1:
                    tp += 1
                else:
                    fp += 1
        flagged = tp + fp
        precision = tp / flagged if flagged else 0.0
        recall = tp / total_pos if total_pos else 0.0
        fpr = fp / total_neg if total_neg else 0.0
        rows.append(
            ThresholdRow(
                threshold=threshold,
                flagged=flagged,
                true_positive=tp,
                false_positive=fp,
                precision=round(precision, 4),
                recall=round(recall, 4),
                false_positive_rate=round(fpr, 4),
            )
        )
    return rows


def reliability_bins(
    probabilities: list[float], labels: list[int], n_bins: int = 10
) -> list[dict]:
    """Group predictions into equal-width probability bins and report the gap
    between predicted and observed rates (the calibration reliability curve)."""
    bins: list[dict] = []
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        idx = [
            i
            for i, p in enumerate(probabilities)
            if (p >= lo and p < hi) or (b == n_bins - 1 and p == hi)
        ]
        if not idx:
            continue
        mean_pred = sum(probabilities[i] for i in idx) / len(idx)
        observed = sum(labels[i] for i in idx) / len(idx)
        bins.append(
            {
                "range": (round(lo, 2), round(hi, 2)),
                "count": len(idx),
                "mean_predicted": round(mean_pred, 4),
                "observed_rate": round(observed, 4),
                "gap": round(observed - mean_pred, 4),
            }
        )
    return bins


def expected_calibration_error(
    probabilities: list[float], labels: list[int], n_bins: int = 10
) -> float | None:
    """Sample-weighted mean |predicted − observed| across reliability bins."""
    if not probabilities:
        return None
    total = len(probabilities)
    error = 0.0
    for b in reliability_bins(probabilities, labels, n_bins):
        error += (b["count"] / total) * abs(b["gap"])
    return round(error, 4)


def wilson_interval(positives: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (better than normal
    approximation at small samples / extreme rates)."""
    if total == 0:
        return (0.0, 1.0)
    phat = positives / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    margin = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


@dataclass
class IsotonicBin:
    score_lo: float
    score_hi: float
    probability: float
    count: int
    positives: int


def fit_isotonic(
    scores: list[float], labels: list[int]
) -> list[IsotonicBin]:
    """Pool-Adjacent-Violators isotonic regression of P(label=1) on score.

    Produces a monotone non-decreasing step function over the score domain,
    compressed into contiguous bins. This is the standard non-parametric
    calibration method — no distributional assumptions, just "higher score
    should not mean lower observed rate".
    """
    if not scores:
        return []

    # 1) Collapse duplicate scores into weighted points (mean label per score).
    by_score: dict[float, list[int]] = {}
    for s, y in zip(scores, labels):
        by_score.setdefault(float(s), []).append(y)
    points = sorted(by_score.items())

    blocks = [
        {
            "lo": s,
            "hi": s,
            "sum": float(sum(ys)),
            "count": len(ys),
        }
        for s, ys in points
    ]

    # 2) PAV: merge while the mean of a block exceeds the next (monotone up).
    merged = True
    while merged:
        merged = False
        i = 0
        while i < len(blocks) - 1:
            a, b = blocks[i], blocks[i + 1]
            if a["sum"] / a["count"] > b["sum"] / b["count"]:
                a["hi"] = b["hi"]
                a["sum"] += b["sum"]
                a["count"] += b["count"]
                del blocks[i + 1]
                merged = True
            else:
                i += 1

    # 3) Materialise contiguous score ranges; widen the ends to cover [0, 100].
    out: list[IsotonicBin] = []
    for index, block in enumerate(blocks):
        lo = 0.0 if index == 0 else block["lo"]
        hi = 100.0 if index == len(blocks) - 1 else block["hi"]
        out.append(
            IsotonicBin(
                score_lo=round(lo, 4),
                score_hi=round(hi, 4),
                probability=round(block["sum"] / block["count"], 6),
                count=int(block["count"]),
                positives=int(round(block["sum"])),
            )
        )
    return out

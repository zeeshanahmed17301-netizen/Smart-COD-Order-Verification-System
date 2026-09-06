"""Backtest the risk engine against real delivery outcomes, and optionally fit
an outcome-backed calibration from the same data.

Predictions = the score stored on each order (computed during its life, before
the courier outcome was known). Labels = the terminal status the order actually
reached. This answers the only question that makes a risk score "industry grade":
does it predict what happened?

    python manage.py evaluate_risk_engine
    python manage.py evaluate_risk_engine --target rto --fit
    python manage.py evaluate_risk_engine --merchant-email a@b.com --bins 5

Label definitions (delivery-outcome only — decision-contaminated statuses like
admin ``cancelled``/``rejected`` are excluded so we measure prediction, not our
own past actions):

    rto:   positive = status "rto",  negative = status "delivered"
    fraud: no ground-truth label exists in the data yet, so fraud is reported as
           "unlabelled" unless you wire an admin-confirmed-fraud flag. We do NOT
           invent a proxy label.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.orders.models import Order
from apps.risk_engine.calibration import fit_and_activate
from apps.risk_engine.metrics import (
    expected_calibration_error,
    precision_recall_table,
    reliability_bins,
    roc_auc,
)

# Score field on Order used as the prediction for each target.
TARGET_SCORE_FIELD = {
    "rto": "rto_probability_score",
    "fraud": "fraud_score",
}

# (positive statuses, negative statuses) for each target's outcome label.
TARGET_LABELS = {
    "rto": ({"rto"}, {"delivered"}),
    # No clean fraud label in the schema yet.
    "fraud": (set(), set()),
}


class Command(BaseCommand):
    help = "Backtest stored risk scores against actual outcomes (+ optional --fit)."

    def add_arguments(self, parser):
        parser.add_argument("--target", choices=["rto", "fraud"], default="rto")
        parser.add_argument("--merchant-email", dest="merchant_email", default=None)
        parser.add_argument("--bins", type=int, default=10, help="Reliability bins.")
        parser.add_argument(
            "--fit",
            action="store_true",
            help="Fit + activate an isotonic calibration from this data.",
        )

    def handle(self, *args, **options):
        target = options["target"]
        positives, negatives = TARGET_LABELS[target]
        if not positives:
            raise CommandError(
                f"Target '{target}' has no ground-truth label in the data yet. "
                "Only 'rto' (delivered-vs-rto) is labellable today."
            )

        score_field = TARGET_SCORE_FIELD[target]
        qs = Order.objects.filter(status__in=positives | negatives)
        if options["merchant_email"]:
            qs = qs.filter(merchant__email=options["merchant_email"])

        scores: list[float] = []
        labels: list[int] = []
        for status, score in qs.values_list("status", score_field):
            scores.append(float(score or 0.0))
            labels.append(1 if status in positives else 0)

        n = len(scores)
        n_pos = sum(labels)
        n_neg = n - n_pos
        label_def = (
            f"positive={sorted(positives)} negative={sorted(negatives)} "
            f"score_field={score_field}"
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nRisk engine backtest — target={target}"))
        self.stdout.write(label_def)
        self.stdout.write(
            f"labelled orders: {n}  (positives={n_pos}, negatives={n_neg})"
        )

        if n_pos == 0 or n_neg == 0:
            self.stdout.write(
                self.style.WARNING(
                    "\nNot enough labelled outcomes in both classes to evaluate. "
                    "Let orders reach delivered/rto, then re-run. (The harness is "
                    "wired and correct — it just needs data.)"
                )
            )
            return

        auc = roc_auc(labels, scores)
        probs = [s / 100.0 for s in scores]
        ece = expected_calibration_error(probs, labels, options["bins"])

        self.stdout.write(self.style.MIGRATE_HEADING("\nDiscrimination"))
        self.stdout.write(f"  ROC-AUC: {auc}   (0.5 = coin flip, 1.0 = perfect)")
        self.stdout.write(f"  base rate: {round(n_pos / n, 4)}")

        self.stdout.write(self.style.MIGRATE_HEADING("\nDecision thresholds (score >= T)"))
        self.stdout.write("   T    flagged   TP   FP   precision   recall   FPR")
        for row in precision_recall_table(labels, scores, [30, 40, 50, 60, 70, 80]):
            self.stdout.write(
                f"  {row.threshold:>3.0f}   {row.flagged:>6}  {row.true_positive:>4} "
                f"{row.false_positive:>4}   {row.precision:>8}  {row.recall:>6}  "
                f"{row.false_positive_rate:>5}"
            )
        self.stdout.write(
            "  (recall = RTO catch rate; FPR = good orders wrongly flagged)"
        )

        self.stdout.write(self.style.MIGRATE_HEADING("\nCalibration reliability (pre-fit)"))
        self.stdout.write(f"  expected calibration error: {ece}  (lower = better)")
        self.stdout.write("   pred-range    n    mean_pred   observed   gap")
        for b in reliability_bins(probs, labels, options["bins"]):
            lo, hi = b["range"]
            self.stdout.write(
                f"  [{lo:.2f},{hi:.2f})  {b['count']:>4}    {b['mean_predicted']:>7}"
                f"    {b['observed_rate']:>7}   {b['gap']:>+.4f}"
            )

        if options["fit"]:
            version = f"{target}-isotonic-{timezone.now():%Y%m%d%H%M%S}"
            model = fit_and_activate(
                target=target,
                scores=scores,
                labels=labels,
                version=version,
                label_definition=label_def,
                auc=auc,
                ece=ece,
                notes=f"Fitted by evaluate_risk_engine on {n} orders.",
            )
            self.stdout.write(self.style.SUCCESS(
                f"\nFitted + activated calibration '{model.version}' "
                f"({len(model.bins)} isotonic bins, n={model.sample_size}). "
                "The scorer now serves outcome-backed probabilities for this target."
            ))
        else:
            self.stdout.write(
                "\nRe-run with --fit to activate an isotonic calibration from this data."
            )

"""Train the RTO logistic-regression challenger from leak-free snapshots.

Training rows = each order's EARLIEST feature snapshot (captured before the
courier outcome existed) paired with the realised delivered/rto label. A holdout
split measures the challenger's ROC-AUC and compares it to the rules baseline
(the order's stored RTO score) on the same holdout — the champion/challenger
comparison that justifies (or refuses) promotion.

    python manage.py train_rto_model                 # train, save as shadow challenger
    python manage.py train_rto_model --promote       # promote to champion if it wins
    python manage.py train_rto_model --holdout 0.25 --seed 1

The model is saved active in 'shadow' role by default: it predicts and records
alongside the rules but does NOT change decisions until promoted.
"""

from __future__ import annotations

import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderFeatureSnapshot
from apps.risk_engine.metrics import roc_auc
from apps.risk_engine.ml import fit_logistic
from apps.risk_engine.models import RiskMLModel

POSITIVE = {"rto"}
NEGATIVE = {"delivered"}
MIN_ROWS = 40


class Command(BaseCommand):
    help = "Train + register the RTO ML challenger from point-in-time snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--holdout", type=float, default=0.2)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--epochs", type=int, default=400)
        parser.add_argument(
            "--promote",
            action="store_true",
            help="Promote to champion if holdout AUC beats the rules baseline.",
        )

    def handle(self, *args, **options):
        orders = {
            o.id: o
            for o in Order.objects.filter(status__in=POSITIVE | NEGATIVE)
        }
        # Earliest snapshot per order = leak-free decision-time features.
        earliest: dict[int, OrderFeatureSnapshot] = {}
        for snap in (
            OrderFeatureSnapshot.objects.filter(order_id__in=orders)
            .order_by("order_id", "generated_at")
        ):
            earliest.setdefault(snap.order_id, snap)

        rows = []
        for order_id, snap in earliest.items():
            order = orders[order_id]
            rows.append((snap.features or {}, 1 if order.status in POSITIVE else 0, float(order.rto_probability_score or 0.0)))

        if len(rows) < MIN_ROWS:
            raise CommandError(
                f"Need at least {MIN_ROWS} labelled (snapshot, outcome) rows to "
                f"train; found {len(rows)}. Let more orders reach delivered/rto."
            )

        rng = random.Random(options["seed"])
        rng.shuffle(rows)
        cut = int(len(rows) * (1 - options["holdout"]))
        train, holdout = rows[:cut], rows[cut:]

        train_pos = sum(y for _, y, _ in train)
        if train_pos == 0 or train_pos == len(train):
            raise CommandError("Training split has only one class — need both delivered and rto.")

        model = fit_logistic(
            [f for f, _, _ in train], [y for _, y, _ in train], epochs=options["epochs"]
        )

        # Evaluate on holdout: challenger vs rules baseline.
        h_labels = [y for _, y, _ in holdout]
        challenger_probs = [model.predict_proba(f) for f, _, _ in holdout]
        baseline_probs = [b / 100.0 for _, _, b in holdout]
        challenger_auc = roc_auc(h_labels, challenger_probs)
        baseline_auc = roc_auc(h_labels, baseline_probs)

        self.stdout.write(self.style.MIGRATE_HEADING("\nRTO challenger training"))
        self.stdout.write(f"  rows: {len(rows)}  (train={len(train)}, holdout={len(holdout)})")
        self.stdout.write(f"  challenger holdout AUC: {challenger_auc}")
        self.stdout.write(f"  rules baseline AUC:     {baseline_auc}")

        wins = (
            challenger_auc is not None
            and baseline_auc is not None
            and challenger_auc > baseline_auc
        )
        role = "champion" if (options["promote"] and wins) else "shadow"

        with transaction.atomic():
            RiskMLModel.objects.filter(target="rto", is_active=True).update(is_active=False)
            saved = RiskMLModel.objects.create(
                target="rto",
                version=f"rto-logreg-{timezone.now():%Y%m%d%H%M%S}",
                algorithm="logistic_regression",
                role=role,
                is_active=True,
                params=model.to_dict(),
                train_size=len(train),
                holdout_size=len(holdout),
                holdout_auc=challenger_auc,
                baseline_auc=baseline_auc,
                notes="Trained by train_rto_model from point-in-time snapshots.",
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nSaved '{saved.version}' active in role '{saved.role}'."
        ))
        if options["promote"] and not wins:
            self.stdout.write(self.style.WARNING(
                "  NOT promoted: challenger did not beat the rules baseline. "
                "Saved as shadow instead — promotion must be earned."
            ))
        elif role == "champion":
            self.stdout.write(
                "  Promoted to champion — it now drives the served RTO probability "
                "(hard rule guardrails still apply)."
            )
        else:
            self.stdout.write("  Shadow mode — predicts alongside the rules without changing decisions.")

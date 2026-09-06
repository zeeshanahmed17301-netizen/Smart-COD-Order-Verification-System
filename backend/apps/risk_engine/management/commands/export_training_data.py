"""Export a leak-free (features → outcome) training matrix as JSONL.

For each order that reached a terminal delivery outcome, we take its EARLIEST
feature snapshot — the one captured at ingestion scoring, before the courier
outcome existed — and pair it with the realised label. Using the earliest
snapshot is what makes the matrix leak-free: it never contains information that
only became available after the prediction was needed.

    python manage.py export_training_data --target rto --output rto_train.jsonl

Each line: {"order_id", "label", "outcome", "schema", "captured_at", <features…>}
Only 'rto' (delivered=0 / rto=1) is labellable today — fraud has no ground truth.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.orders.models import Order, OrderFeatureSnapshot

TARGET_LABELS = {
    "rto": ({"rto"}, {"delivered"}),
}


class Command(BaseCommand):
    help = "Export leak-free features→label training data (JSONL) from snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--target", choices=["rto"], default="rto")
        parser.add_argument("--merchant-email", dest="merchant_email", default=None)
        parser.add_argument(
            "--output",
            default=None,
            help="File to write JSONL to (default: stdout).",
        )

    def handle(self, *args, **options):
        target = options["target"]
        positives, negatives = TARGET_LABELS[target]

        orders = Order.objects.filter(status__in=positives | negatives)
        if options["merchant_email"]:
            orders = orders.filter(merchant__email=options["merchant_email"])

        # Earliest snapshot per order = point-in-time decision features.
        earliest: dict[int, OrderFeatureSnapshot] = {}
        snaps = (
            OrderFeatureSnapshot.objects.filter(order__in=orders)
            .order_by("order_id", "generated_at")
        )
        for snap in snaps:
            earliest.setdefault(snap.order_id, snap)

        rows: list[str] = []
        labelled = {o.id: o.status for o in orders}
        for order_id, snap in earliest.items():
            status = labelled.get(order_id)
            if status is None:
                continue
            record = {
                "order_id": order_id,
                "label": 1 if status in positives else 0,
                "outcome": status,
                "schema": snap.feature_schema_version,
                "captured_at": snap.generated_at.isoformat(),
                **(snap.features or {}),
            }
            rows.append(json.dumps(record, default=str, sort_keys=True))

        if not rows:
            raise CommandError(
                "No (snapshot, outcome) pairs found. Snapshots are captured on "
                "every scoring pass from now on — once these orders reach "
                "delivered/rto you'll get training rows. (Older orders scored "
                "before this feature have no snapshot.)"
            )

        output = "\n".join(rows) + "\n"
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as handle:
                handle.write(output)
            self.stdout.write(self.style.SUCCESS(
                f"Wrote {len(rows)} training rows to {options['output']}."
            ))
        else:
            self.stdout.write(output)

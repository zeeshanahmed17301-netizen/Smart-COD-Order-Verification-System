"""Bulk re-score existing orders with the current risk engine logic."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.orders.models import Order
from apps.risk_engine.services import RiskScoringEngine
from apps.stores.shopify_sync import refresh_shopify_order_bootstrap


class Command(BaseCommand):
    help = "Refresh imported Shopify features, then re-score existing orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--merchant-email",
            dest="merchant_email",
            help="Only re-score orders for this merchant email.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Only process the first N matching orders.",
        )
        parser.add_argument(
            "--only-missing-calibration",
            action="store_true",
            help="Only process orders with an empty calibration version.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate scores without saving them.",
        )

    def handle(self, *args, **options):
        merchant_email = options["merchant_email"]
        limit = max(int(options["limit"] or 0), 0)
        only_missing_calibration = options["only_missing_calibration"]
        dry_run = options["dry_run"]

        queryset = (
            Order.objects
            .select_related("merchant", "customer", "address", "source_snapshot", "enrichment")
            .prefetch_related("items")
            .order_by("id")
        )
        if merchant_email:
            queryset = queryset.filter(merchant__email=merchant_email)
        if only_missing_calibration:
            queryset = queryset.filter(score_calibration_version="")
        if limit:
            queryset = queryset[:limit]

        processed = 0
        failed = 0
        for order in queryset.iterator(chunk_size=200):
            try:
                if dry_run:
                    RiskScoringEngine.calculate(order)
                else:
                    refresh_shopify_order_bootstrap(order)
                    RiskScoringEngine.score_and_save(order, skip_chatbot=True)
                processed += 1
            except Exception as exc:  # noqa: BLE001 - keep bulk jobs moving
                failed += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed to score order {order.order_id}: {exc}"
                    )
                )

        mode = "calculated" if dry_run else "rescored"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode.capitalize()} {processed} orders with {failed} failures."
            )
        )

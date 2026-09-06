"""Import courier branches from results.json into the CourierBranch table."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.addresses.courier_coverage import (
    extract_city_from_address,
    extract_city_from_branch_name,
    invalidate_coverage_cache,
    normalize_city,
)
from apps.addresses.models import CourierBranch


class Command(BaseCommand):
    help = "Import courier branch data from results.json into the database."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            default=str(Path(__file__).resolve().parents[5] / "results.json"),
            help="Path to results.json (default: project root).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing branches before importing.",
        )

    def handle(self, *args, **options) -> None:
        filepath = options["file"]
        self.stdout.write(f"Loading courier data from: {filepath}")

        try:
            with open(filepath, encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            self.stderr.write(self.style.ERROR(f"Failed to load file: {exc}"))
            return

        if options["clear"]:
            deleted, _ = CourierBranch.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing branches."))

        created_count = 0
        skipped_count = 0

        for company in data:
            brand = company.get("canonical_name") or company.get("brand", "")
            status = company.get("status", "")
            branches = company.get("branches", [])

            if status != "ok" or not branches:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping {brand} (status={status}, branches={len(branches)})")
                )
                continue

            self.stdout.write(f"  Processing {brand}: {len(branches)} branches")

            for branch_data in branches:
                branch_name = branch_data.get("branch_name", "")
                address = branch_data.get("address", "")

                # Derive city from branch name, falling back to address
                city_from_name = extract_city_from_branch_name(branch_name)
                city_from_addr = extract_city_from_address(address)
                city_raw = city_from_name or city_from_addr
                city_normalized = normalize_city(city_raw)

                if not city_normalized:
                    skipped_count += 1
                    continue

                CourierBranch.objects.update_or_create(
                    brand=brand,
                    branch_name=branch_name,
                    defaults={
                        "address": address,
                        "phone": branch_data.get("phone", ""),
                        "url": branch_data.get("url", ""),
                        "city_raw": city_raw,
                        "city_normalized": city_normalized,
                        "is_active": True,
                    },
                )
                created_count += 1

        # Invalidate the in-memory coverage cache
        invalidate_coverage_cache()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Imported {created_count} branches, skipped {skipped_count}."
            )
        )

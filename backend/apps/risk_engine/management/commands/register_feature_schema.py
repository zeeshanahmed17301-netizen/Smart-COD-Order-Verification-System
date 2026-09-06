"""Upsert the active FeatureSchemaVersion row from the code-defined contract.

The feature contract lives in ``apps/risk_engine/features.py`` (the source of
truth). This command publishes it into the ``FeatureSchemaVersion`` table so
offline consumers / dashboards can read the contract a snapshot was written
against. Safe to run repeatedly.

    python manage.py register_feature_schema
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ml_models.models import FeatureSchemaVersion
from apps.risk_engine.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION

# Tri-state features may legitimately be null (unknown), so they are not required.
NULLABLE_FEATURES = {"courier_available", "ip_geo_matches_shipping_city"}


class Command(BaseCommand):
    help = "Publish the code feature contract into FeatureSchemaVersion."

    def handle(self, *args, **options):
        required = [name for name in FEATURE_NAMES if name not in NULLABLE_FEATURES]
        schema, created = FeatureSchemaVersion.objects.update_or_create(
            version=FEATURE_SCHEMA_VERSION,
            defaults={
                "target": "shared",
                "is_active": True,
                "feature_names": FEATURE_NAMES,
                "required_feature_names": required,
                "notes": "Auto-published from apps.risk_engine.features.FEATURE_NAMES.",
            },
        )
        # Exactly one active schema per the active contract version.
        FeatureSchemaVersion.objects.exclude(pk=schema.pk).filter(is_active=True).update(
            is_active=False
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} active FeatureSchemaVersion '{FEATURE_SCHEMA_VERSION}' "
            f"with {len(FEATURE_NAMES)} features ({len(required)} required)."
        ))

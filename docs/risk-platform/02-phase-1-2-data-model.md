# Phase 1 And Phase 2 Data Model Design

This document defines the Django model changes for the first two major implementation phases.

## Design Principles

- keep `Order` as the central scored entity
- keep `OrderSourceSnapshot` for raw ingestion payloads
- keep `OrderEnrichment` for online hot-path derived fields
- add new models for versioning, telemetry, and reproducible feature snapshots
- avoid turning `OrderEnrichment` into the full offline feature store

## App Placement

Use the following app boundaries:

- `apps/orders`
  - order state
  - source snapshots
  - online enrichment
  - feature snapshots
- `apps/risk_engine`
  - scoring config
  - labels
  - calibration
  - decision policy
- `apps.telemetry`
  - browser, session, and device event storage
- `apps.ml_models`
  - feature schemas, model artifacts, training runs

## Phase 1: Data Capture Changes

### Extend `Order`

File:

- `backend/apps/orders/models.py`

Add fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `score_source` | `CharField(max_length=20)` | `rules`, `ml`, `hybrid`, `fallback` |
| `feature_schema_version` | `CharField(max_length=32, blank=True, default="")` | feature contract used at scoring time |
| `fraud_model_version` | `CharField(max_length=64, blank=True, default="")` | frozen fraud model version |
| `rto_model_version` | `CharField(max_length=64, blank=True, default="")` | frozen RTO model version |
| `decision_policy_version` | `CharField(max_length=32, blank=True, default="")` | policy version used for action |
| `rescored_at` | `DateTimeField(null=True, blank=True)` | last scoring time |

Indexes:

- `(merchant, created_at)`
- `(merchant, score_source, created_at)`
- `(feature_schema_version, created_at)`

### Extend `OrderSourceSnapshot`

Add fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `checkout_session_id` | `CharField(max_length=128, blank=True)` | frontend session correlation |
| `device_fingerprint_id` | `CharField(max_length=128, blank=True)` | provider or internal fingerprint token |
| `referrer_url` | `URLField(blank=True)` | acquisition context |
| `landing_page_url` | `URLField(blank=True)` | campaign/page context |
| `utm_source` | `CharField(max_length=100, blank=True)` | attribution |
| `utm_medium` | `CharField(max_length=100, blank=True)` | attribution |
| `utm_campaign` | `CharField(max_length=100, blank=True)` | attribution |
| `accept_language` | `CharField(max_length=255, blank=True)` | browser consistency |
| `timezone_name` | `CharField(max_length=64, blank=True)` | session consistency |
| `screen_resolution` | `CharField(max_length=32, blank=True)` | device/browser telemetry |
| `risk_facts_payload` | `JSONField(default=dict, blank=True)` | normalized fraud facts from platform/provider |

Indexes:

- `(client_ip, imported_at)`
- `(device_fingerprint_id, imported_at)`
- `(checkout_session_id, imported_at)`
- `(source_name, imported_at)`

### Extend `OrderEnrichment`

Add address-validation fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `address_validation_verdict` | `CharField(max_length=50, blank=True)` | provider verdict summary |
| `address_complete` | `BooleanField(null=True, blank=True)` | complete vs partial |
| `address_has_unconfirmed_components` | `BooleanField(null=True, blank=True)` | provider verdict flag |
| `address_has_inferred_components` | `BooleanField(null=True, blank=True)` | provider verdict flag |
| `address_has_replaced_components` | `BooleanField(null=True, blank=True)` | provider verdict flag |
| `address_possible_next_action` | `CharField(max_length=50, blank=True)` | fix / confirm / accept style verdict |
| `geocode_granularity` | `CharField(max_length=50, blank=True)` | premise / locality / route |
| `validation_granularity` | `CharField(max_length=50, blank=True)` | provider validation detail |
| `deliverability_verdict` | `CharField(max_length=50, blank=True)` | deliverable / uncertain / poor |
| `validation_metadata` | `JSONField(default=dict, blank=True)` | trimmed provider metadata |

Add network/device fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `ip_asn` | `CharField(max_length=32, blank=True)` | network identity |
| `ip_isp` | `CharField(max_length=255, blank=True)` | provider / ISP |
| `ip_organization` | `CharField(max_length=255, blank=True)` | org metadata |
| `ip_connection_type` | `CharField(max_length=64, blank=True)` | residential / mobile / corporate / hosting |
| `device_first_seen_at` | `DateTimeField(null=True, blank=True)` | fraud graphing |
| `device_order_count_30d` | `PositiveIntegerField(default=0)` | velocity |
| `device_customer_count_30d` | `PositiveIntegerField(default=0)` | many-users-per-device signal |
| `session_order_count_24h` | `PositiveIntegerField(default=0)` | velocity |
| `email_order_count_30d` | `PositiveIntegerField(default=0)` | identity velocity |

Add logistics fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `destination_postal_cluster` | `CharField(max_length=32, blank=True)` | pincode/cluster feature join |
| `carrier_rto_rate_30d` | `FloatField(default=0.0)` | logistics performance |
| `carrier_delivery_rate_30d` | `FloatField(default=0.0)` | logistics performance |
| `ndr_rate_30d` | `FloatField(default=0.0)` | non-delivery rate |
| `estimated_delivery_days` | `FloatField(default=0.0)` | SLA risk |

Indexes:

- `(ip_provider, ip_country, created_at)`
- `(device_customer_count_30d, created_at)`
- `(destination_postal_cluster, created_at)`

### Extend `Address`

Add fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `validation_provider` | `CharField(max_length=50, blank=True)` | current source of truth |
| `validation_verdict` | `CharField(max_length=50, blank=True)` | provider-level verdict |
| `formatted_address` | `TextField(blank=True)` | standardized address |
| `subpremise` | `CharField(max_length=100, blank=True)` | apartment/unit detail |
| `country_code` | `CharField(max_length=8, blank=True)` | normalized ISO code |
| `district` | `CharField(max_length=100, blank=True)` | logistics segmentation |
| `address_granularity` | `CharField(max_length=50, blank=True)` | premise/locality/route |
| `deliverability_metadata` | `JSONField(default=dict, blank=True)` | provider deliverability summary |
| `last_validated_at` | `DateTimeField(null=True, blank=True)` | freshness |

Indexes:

- `(city, postal_code)`
- `(country_code, postal_code)`
- `(validation_verdict, last_validated_at)`

### New Model: `RiskSession`

App:

- `apps/telemetry`

Fields:

| Field | Type |
| --- | --- |
| `session_id` | `CharField(max_length=128, unique=True)` |
| `merchant` | `ForeignKey(User)` |
| `customer` | `ForeignKey(Customer, null=True, blank=True)` |
| `device_fingerprint_id` | `CharField(max_length=128, blank=True)` |
| `client_ip` | `GenericIPAddressField(null=True, blank=True)` |
| `user_agent` | `TextField(blank=True)` |
| `accept_language` | `CharField(max_length=255, blank=True)` |
| `timezone_name` | `CharField(max_length=64, blank=True)` |
| `landing_page_url` | `URLField(blank=True)` |
| `referrer_url` | `URLField(blank=True)` |
| `utm_payload` | `JSONField(default=dict, blank=True)` |
| `started_at` | `DateTimeField(auto_now_add=True)` |
| `last_seen_at` | `DateTimeField(auto_now=True)` |

Indexes:

- `(merchant, started_at)`
- `(device_fingerprint_id, last_seen_at)`
- `(client_ip, last_seen_at)`

### New Model: `RiskTelemetryEvent`

App:

- `apps/telemetry`

Fields:

| Field | Type |
| --- | --- |
| `session` | `ForeignKey(RiskSession)` |
| `order` | `ForeignKey(Order, null=True, blank=True)` |
| `event_type` | `CharField(max_length=50)` |
| `event_payload` | `JSONField(default=dict)` |
| `schema_version` | `CharField(max_length=32)` |
| `occurred_at` | `DateTimeField()` |
| `created_at` | `DateTimeField(auto_now_add=True)` |

Indexes:

- `(session, occurred_at)`
- `(order, occurred_at)`
- `(event_type, occurred_at)`

### New Model: `CarrierOutcomeEvent`

App:

- `apps/risk_engine`

Fields:

| Field | Type |
| --- | --- |
| `order` | `ForeignKey(Order)` |
| `carrier_name` | `CharField(max_length=100)` |
| `event_type` | `CharField(max_length=50)` |
| `event_status` | `CharField(max_length=50, blank=True)` |
| `event_reason_code` | `CharField(max_length=64, blank=True)` |
| `event_note` | `TextField(blank=True)` |
| `attempt_number` | `PositiveIntegerField(default=0)` |
| `occurred_at` | `DateTimeField()` |
| `raw_payload` | `JSONField(default=dict, blank=True)` |
| `created_at` | `DateTimeField(auto_now_add=True)` |

Indexes:

- `(order, occurred_at)`
- `(carrier_name, event_type, occurred_at)`

## Phase 2: Feature Platform Changes

### New Model: `FeatureSchemaVersion`

App:

- `apps/ml_models`

Fields:

| Field | Type |
| --- | --- |
| `version` | `CharField(max_length=32, unique=True)` |
| `target` | `CharField(max_length=20)` |
| `is_active` | `BooleanField(default=False)` |
| `feature_names` | `JSONField(default=list)` |
| `required_feature_names` | `JSONField(default=list)` |
| `notes` | `TextField(blank=True)` |
| `created_at` | `DateTimeField(auto_now_add=True)` |

Indexes:

- `(target, is_active)`

### New Model: `OrderFeatureSnapshot`

App:

- `apps/orders`

Purpose:

- immutable feature vector used for scoring or training extraction

Fields:

| Field | Type |
| --- | --- |
| `order` | `ForeignKey(Order, related_name="feature_snapshots")` |
| `feature_schema_version` | `CharField(max_length=32)` |
| `snapshot_type` | `CharField(max_length=20)` |
| `generated_by` | `CharField(max_length=30)` |
| `features` | `JSONField(default=dict)` |
| `feature_hash` | `CharField(max_length=64, db_index=True)` |
| `generated_at` | `DateTimeField(auto_now_add=True)` |

Recommended `snapshot_type` values:

- `online_scoring`
- `training`
- `backfill`

Indexes:

- `(order, generated_at)`
- `(feature_schema_version, generated_at)`
- `(snapshot_type, generated_at)`

### New Model: `FeatureAggregateWindow`

App:

- `apps/ml_models`

Purpose:

- generic aggregate table to avoid multiple one-off aggregate models for every dimension

Fields:

| Field | Type |
| --- | --- |
| `entity_type` | `CharField(max_length=32)` |
| `entity_key` | `CharField(max_length=128)` |
| `window_name` | `CharField(max_length=32)` |
| `metrics` | `JSONField(default=dict)` |
| `computed_at` | `DateTimeField()` |
| `created_at` | `DateTimeField(auto_now_add=True)` |
| `updated_at` | `DateTimeField(auto_now=True)` |

Recommended `entity_type` values:

- `customer`
- `device`
- `source`
- `postal_cluster`
- `category`
- `carrier_lane`

Indexes:

- `(entity_type, entity_key, window_name)`
- `(window_name, computed_at)`

### New Model: `TrainingLabel`

App:

- `apps/risk_engine`

Purpose:

- target-specific labels with provenance

Fields:

| Field | Type |
| --- | --- |
| `order` | `ForeignKey(Order, related_name="training_labels")` |
| `target` | `CharField(max_length=20)` |
| `label` | `CharField(max_length=50)` |
| `label_value` | `FloatField()` |
| `label_source` | `CharField(max_length=50)` |
| `is_final` | `BooleanField(default=False)` |
| `recorded_at` | `DateTimeField(auto_now_add=True)` |
| `metadata` | `JSONField(default=dict, blank=True)` |

Indexes:

- `(target, is_final, recorded_at)`
- `(order, target)`

## Migration Strategy

Use this sequence:

1. extend existing `Order`, `OrderSourceSnapshot`, `OrderEnrichment`, and `Address`
2. add `apps/telemetry` models
3. add `CarrierOutcomeEvent`
4. add `FeatureSchemaVersion`
5. add `OrderFeatureSnapshot`
6. add `FeatureAggregateWindow`
7. add `TrainingLabel`

## Backfill Strategy

Backfills needed after migration:

- bootstrap session ids from existing `OrderSourceSnapshot.session_hash`
- populate address validation fields with heuristic fallback defaults
- populate logistics aggregates from historical `OutcomeRecord`
- generate initial `OrderFeatureSnapshot` rows for scored orders

## Explicit Non-Goals For Phase 1 And 2

Do not add these yet:

- model binary artifacts
- full training run records
- champion/challenger tables
- review queue models

Those belong in later phases after feature platform stabilization.

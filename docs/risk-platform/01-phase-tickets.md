# Risk Platform Phase Tickets

This file converts the platform roadmap into repo-oriented implementation tickets.

## Phase 0: Stabilize The Current Engine

### RP-0001: Expose Raw And Calibrated Scores In APIs

Goal:

- expose both raw score and calibrated probability for fraud and RTO
- make UI and analytics distinguish raw score from calibrated probability

Scope:

- update `apps/orders/serializers.py`
- update risk detail payloads
- update frontend orders and order detail screens

Acceptance criteria:

- list and detail APIs expose `fraud_score_raw`, `fraud_probability`, `rto_score_raw`, `rto_probability_percent`
- operator can see calibration version and score source
- no field-name ambiguity remains in frontend labels

Dependencies:

- none

### RP-0002: Add Score Diagnostics To Saved Orders

Goal:

- persist enough metadata to audit how a score was produced

Scope:

- extend `Order`
- persist score source, versions, and last rescored timestamp

Acceptance criteria:

- every rescored order stores score source and timestamps
- admin and API expose these diagnostics

Dependencies:

- RP-0001 optional

### RP-0003: Add Distribution And Drift Observability For Current Scores

Goal:

- quantify score collapse and low-signal saturation before ML rollout

Scope:

- management command for score distribution summary
- merchant-level histogram endpoints or admin reports

Acceptance criteria:

- can inspect score distributions by merchant and time window
- can measure percentage of orders falling into each calibration band

Dependencies:

- RP-0001

## Phase 1: Industry-Grade Data Capture

### RP-1001: Introduce Address Validation Provider Abstraction

Goal:

- support real address validation with verdict, geocode, and deliverability metadata

Scope:

- add `apps/risk_engine/address_validation.py`
- provider interface for Google Maps Address Validation or equivalent
- fallback to current heuristic logic

Acceptance criteria:

- provider can be enabled via settings
- response is normalized to one internal verdict contract
- failures degrade to heuristic path without breaking scoring

Dependencies:

- none

### RP-1002: Extend Address And Enrichment Models For Validation Verdicts

Goal:

- persist structured address-validation outcomes instead of only heuristic labels

Scope:

- extend `Address`
- extend `OrderEnrichment`
- add migrations and admin exposure

Acceptance criteria:

- validation verdict, completeness, granularity, and provider response summary are persisted
- scoring uses provider verdict fields when present

Dependencies:

- RP-1001

### RP-1003: Add Browser Telemetry Capture Pipeline

Goal:

- capture session and browser attributes needed for fraud graphing

Scope:

- new backend app `apps/telemetry`
- frontend session collector
- telemetry ingestion endpoint

Acceptance criteria:

- stable `session_id` is captured and linked to order
- browser telemetry is stored before or at order creation time
- telemetry schema version is persisted

Dependencies:

- none

### RP-1004: Add Device Fingerprint Support

Goal:

- link orders to devices across sessions and users

Scope:

- add device identifier model
- attach device id to order/session
- support provider-backed or in-house fingerprint token

Acceptance criteria:

- one order can be linked to a device profile
- enrichment can query device reuse and device-to-user graph features

Dependencies:

- RP-1003

### RP-1005: Extend IP Intelligence And Network Metadata

Goal:

- capture richer network features beyond proxy flags

Scope:

- ASN
- ISP / organization
- connection type
- hosting classification
- network country mismatch

Acceptance criteria:

- IP provider response persists structured network metadata
- enrichment derives graph and velocity features from network identity

Dependencies:

- current IP intelligence service

### RP-1006: Capture Courier And Shipment Event Feed

Goal:

- bring logistics-grade events into RTO scoring

Scope:

- add carrier outcome event model
- ingest shipment lifecycle events

Acceptance criteria:

- shipment attempts, failures, NDR, and final carrier outcomes are stored
- order timeline can be reconstructed from events

Dependencies:

- none

## Phase 2: Feature Platform

### RP-2001: Create Feature Schema Versioning

Goal:

- version every online and training feature set

Scope:

- add `FeatureSchemaVersion`
- add validation service for required feature lists

Acceptance criteria:

- scoring path resolves an active feature schema version
- training jobs can select rows by feature schema version

Dependencies:

- Phase 1 data capture tickets

### RP-2002: Add Order Feature Snapshot Model

Goal:

- persist reproducible feature vectors per scored order

Scope:

- add `OrderFeatureSnapshot`
- store feature values as JSON plus promoted key columns

Acceptance criteria:

- each score event can create one feature snapshot
- snapshot stores schema version and generation timestamp

Dependencies:

- RP-2001

### RP-2003: Build Feature Refresh Service

Goal:

- centralize online feature computation and backfill logic

Scope:

- `FeatureRefreshService`
- replace scattered feature derivation with a single orchestration layer

Acceptance criteria:

- rescoring and imports use the same feature refresh pipeline
- backfills can rebuild feature snapshots deterministically

Dependencies:

- RP-2001
- RP-2002

### RP-2004: Add Aggregate Feature Tables

Goal:

- support low-latency windowed features without scanning raw orders each time

Scope:

- customer aggregate windows
- source aggregate windows
- pincode / locality aggregate windows
- category aggregate windows
- device aggregate windows

Acceptance criteria:

- aggregate tables refresh incrementally
- online scoring reads aggregates instead of computing heavy queries ad hoc

Dependencies:

- RP-2003

### RP-2005: Add Feature Backfill Command And Jobs

Goal:

- rebuild feature snapshots for existing historical orders

Scope:

- management command
- merchant-scoped backfill
- date-range support

Acceptance criteria:

- historical orders can be backfilled by merchant and time range
- dry-run mode reports expected row counts

Dependencies:

- RP-2002
- RP-2003

## Phase 3: Calibration

### RP-3001: Build Calibration Dataset Extraction

Goal:

- create predicted-vs-observed datasets for fraud and RTO

Scope:

- training extract from scored orders and labels
- separate target definitions

Acceptance criteria:

- calibration datasets can be rebuilt for a versioned time window

Dependencies:

- Phase 2

### RP-3002: Support Learned Calibration Artifacts

Goal:

- replace seeded bands with trained calibration outputs

Scope:

- add calibration artifact storage
- support isotonic or Platt calibration

Acceptance criteria:

- score serving reads artifact by version
- fallback to seeded bands only when artifact is unavailable

Dependencies:

- RP-3001

## Phase 4: ML Models

### RP-4001: Build Fraud Training Pipeline

Goal:

- train fraud model from feature snapshots and labels

Scope:

- XGBoost or Gradient Boosting baseline
- time-based validation

Acceptance criteria:

- training run stores metrics, artifacts, and feature schema version

Dependencies:

- Phase 2
- Phase 3

### RP-4002: Build RTO Training Pipeline

Goal:

- train separate RTO model

Scope:

- shipment and delivery features
- COD- and logistics-specific signals

Acceptance criteria:

- RTO model is trained and evaluated independently from fraud model

Dependencies:

- RP-4001 parallelizable after shared pipeline pieces exist

### RP-4003: Add Model Registry And Champion/Challenger

Goal:

- manage frozen model artifacts and promotion

Scope:

- model registry models
- serving lookup
- shadow scoring support

Acceptance criteria:

- one champion per target
- challengers can run in shadow mode without affecting decisions

Dependencies:

- RP-4001
- RP-4002

## Phase 5: Decisioning And Review Operations

### RP-5001: Separate Decision Policy From Scoring

Goal:

- apply merchant-specific action policies after scoring

Scope:

- decision policy versioning
- policy service

Acceptance criteria:

- fraud/RTO probabilities no longer directly imply actions
- policies can be changed without retraining models

Dependencies:

- Phase 4

### RP-5002: Build Review Queue And Override Tracking

Goal:

- support manual review and feedback loops

Scope:

- review decision model
- queue endpoints
- operator actions

Acceptance criteria:

- reviewer decisions are stored with reason and actor
- overrides are auditable and usable for label quality analysis

Dependencies:

- RP-5001

## Phase 6: Monitoring And Governance

### RP-6001: Add Calibration And Feature Drift Monitoring

Goal:

- detect degradation early

Scope:

- weekly metrics job
- merchant and global drift views

Acceptance criteria:

- platform can alert on calibration shift, feature missingness, and score collapse

Dependencies:

- Phase 4

### RP-6002: Add Model Performance And Rollback Playbook

Goal:

- make promotion and rollback operationally safe

Scope:

- runbook
- health checks
- rollback endpoint or admin action

Acceptance criteria:

- champion can be rolled back without schema changes
- fallback heuristics can be re-enabled quickly

Dependencies:

- RP-4003

## Suggested Delivery Order

Recommended sequence:

1. RP-0001
2. RP-0002
3. RP-1001
4. RP-1002
5. RP-1003
6. RP-1004
7. RP-1005
8. RP-1006
9. RP-2001
10. RP-2002
11. RP-2003
12. RP-2004
13. RP-2005
14. RP-3001
15. RP-3002
16. RP-4001
17. RP-4002
18. RP-4003
19. RP-5001
20. RP-5002
21. RP-6001
22. RP-6002

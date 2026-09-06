# Risk Platform Architecture

## Goal

Evolve the current `risk_engine` from a heuristic scoring module into an industry-grade decisioning platform for:

- fraud risk
- COD/RTO risk
- operator review workflows
- model calibration and monitoring
- offline training and online frozen-model scoring

The design must preserve current business continuity while allowing staged migration from rules to machine learning.

## Current State Summary

The current platform already has:

- order, customer, address, and source snapshot models
- staged enrichment
- heuristic address/fraud/RTO formulas
- calibrated probability bands
- score breakdown payloads
- outcome recording

The current gaps are:

- no true device fingerprinting or behavioral telemetry
- no real address-validation verdict model
- no logistics-grade RTO features at pincode/lane/carrier level
- no feature store or feature schema versioning
- no frozen model artifact registry
- no offline training pipeline
- no monitoring for calibration drift, feature drift, or approval quality

## Target Architecture

The target platform has six layers:

1. data capture
2. feature computation
3. scoring and calibration
4. decisioning and operations
5. feedback and labeling
6. model lifecycle management

### 1. Data Capture Layer

Primary sources:

- Shopify order and fraud/risk snapshots
- browser and device telemetry from frontend
- IP intelligence provider
- address validation provider
- carrier and shipment outcome events
- WhatsApp / confirmation outcomes
- operator actions

Backend modules:

- `apps/orders`
- `apps/stores`
- `apps/risk_engine`
- new `apps/telemetry`
- new `apps/ml_models`

Frontend additions:

- browser telemetry collector on checkout and order confirmation flows
- stable session id capture
- device fingerprint token capture through approved provider or in-house SDK

### 2. Feature Computation Layer

Split features into three groups:

- online features needed synchronously at scoring time
- nearline aggregates refreshed in batch
- offline training features built from labeled history

Feature families:

- identity features
- address and deliverability features
- device and network features
- behavioral and velocity features
- merchant and source features
- logistics and RTO features
- confirmation and communication features
- payment and platform risk features

New services:

- `FeatureRefreshService`
- `FeatureSchemaService`
- `FeatureBackfillService`
- `FeatureValidationService`

Storage strategy:

- continue storing hot online features on `OrderEnrichment`
- add versioned feature snapshot model for training reproducibility
- add batch aggregate tables for merchant/source/pincode/category/customer windows

### 3. Scoring and Calibration Layer

Scoring becomes a two-track system.

Track A: rules and heuristics

- remains as fallback
- remains primary during transition
- continues to generate operator explanations

Track B: model-based scoring

- separate fraud model
- separate RTO model
- frozen model artifact per target
- explicit feature schema version
- explicit calibration version

Output contract per target:

- raw model score
- calibrated probability
- confidence interval
- top contributing factors
- model version
- feature schema version
- calibration version
- fallback status

New services:

- `FraudModelScoringService`
- `RTOModelScoringService`
- `CalibrationService`
- `ExplanationService`
- `ChampionChallengerService`

### 4. Decisioning and Operations Layer

Decisioning must be separated from scoring.

Scoring answers:

- how likely is fraud?
- how likely is RTO?

Decisioning answers:

- ship
- verify
- manual review
- hold
- cancel
- route to senior analyst

Decision inputs:

- calibrated probabilities
- merchant-specific thresholds
- business rules
- information-quality coverage
- operational constraints

New modules:

- `DecisionPolicyService`
- `ManualReviewQueueService`
- `ThresholdPolicyService`
- `ActionAuditService`

### 5. Feedback and Labeling Layer

Labels must be explicit and target-specific.

Fraud labels:

- confirmed fraud
- chargeback fraud
- prank / fake order
- false positive

RTO labels:

- delivered
- RTO refused
- RTO wrong address
- RTO unreachable
- RTO failed attempts

Operational labels:

- reviewed approve
- reviewed reject
- customer confirmed
- customer ghosted

New models:

- `OrderLabel`
- `LabelSource`
- `ReviewDecision`
- `CarrierOutcomeEvent`

### 6. Model Lifecycle Layer

The ML layer needs reproducibility and safe promotion.

Required components:

- offline training job
- feature extraction pipeline
- training dataset snapshots
- model registry
- champion/challenger metadata
- offline evaluation reports
- calibration artifact generation

New module:

- `apps/ml_models`

Core models:

- `ModelArtifact`
- `ModelVersion`
- `CalibrationArtifact`
- `FeatureSchemaVersion`
- `TrainingRun`
- `EvaluationReport`

## Domain Model Changes

### Keep

- `Order`
- `OrderEnrichment`
- `OutcomeRecord`
- `RiskConfig`
- `ScoreCalibrationVersion`
- `ScoreCalibrationBand`

### Add

- `OrderFeatureSnapshot`
- `FeatureSchemaVersion`
- `FraudLabel`
- `RTOLabel`
- `ReviewDecision`
- `CarrierOutcomeEvent`
- `ModelArtifact`
- `ModelVersion`
- `CalibrationArtifact`
- `TrainingRun`
- `EvaluationReport`
- `RiskTelemetryEvent`

### Extend Existing Models

`Order`

- `fraud_model_version`
- `rto_model_version`
- `feature_schema_version`
- `decision_policy_version`
- `score_source` with values such as `rules`, `ml`, `hybrid`, `fallback`
- `rescored_at`

`OrderEnrichment`

- device id / fingerprint fields
- user-agent derived fields
- ASN / ISP / hosting metadata
- geocode verdict fields
- address validation verdict fields
- pincode / district / route features
- carrier reliability window features

## Feature Roadmap

### Fraud Features

Identity:

- normalized phone reuse across names
- email age / domain quality when available
- repeat customer graph

Device and network:

- device fingerprint stability
- device-user cardinality
- IP-user cardinality
- ASN / hosting / proxy / TOR / VPN
- session velocity
- browser consistency

Behavior:

- checkout dwell time
- retries and repeated attempts
- multi-account linking
- unusual browsing or rapid order creation

Platform:

- Shopify risk assessment facts
- CVV / AVS / 3DS / payment-auth outcomes when available

### RTO Features

Address:

- validated address verdict
- geocode granularity
- deliverability metadata
- pincode-level historical delivery rates
- address correction burden

Customer:

- delivered / RTO / refusal / unreachable rates
- confirmation responsiveness
- time-to-confirm

Logistics:

- courier performance by pincode
- lane-level RTO history
- expected delivery time
- NDR incidence

Order:

- COD / prepaid
- amount
- category
- SKU/product text embeddings later
- order timing and seasonal effects

## Implementation Phases

### Phase 0: Stabilize Current Rules Engine

Scope:

- finish bootstrap refresh and backfills
- improve raw score observability
- expose raw score plus calibrated probability in UI
- add score-source diagnostics

Deliverables:

- reliable rescoring
- clearer operator payloads
- analytics dashboard for score distribution

### Phase 1: Industry-Grade Data Capture

Scope:

- integrate real address validation provider
- integrate browser/device telemetry
- enrich IP intelligence fields
- store raw validation verdicts instead of only heuristic labels

Deliverables:

- `apps/telemetry`
- frontend collector
- provider abstraction for address validation
- device/session identifiers linked to order

Success criteria:

- materially wider score spread
- fewer orders collapsing into identical low-risk bands

### Phase 2: Feature Platform

Scope:

- add versioned feature schema
- add feature snapshot table
- add aggregate windows by merchant, source, customer, pincode, category
- implement backfill jobs

Deliverables:

- `FeatureSchemaVersion`
- `OrderFeatureSnapshot`
- `FeatureRefreshService`
- reproducible training rows

### Phase 3: Better Calibration and Hybrid Scoring

Scope:

- replace seeded calibration bands with merchant-validated calibration artifacts
- support isotonic or Platt calibration offline
- keep heuristic model as fallback

Deliverables:

- calibration training job
- calibration artifact registry
- hybrid score payload

### Phase 4: Fraud and RTO Models

Scope:

- train separate fraud and RTO models
- start with Gradient Boosting / XGBoost
- build offline evaluation and drift reporting

Deliverables:

- `fraud_v1` model artifact
- `rto_v1` model artifact
- explainability output
- champion/challenger support

### Phase 5: Decisioning Layer and Operations

Scope:

- separate probability from action
- merchant-specific decision policies
- review queues and override tracking

Deliverables:

- `DecisionPolicyService`
- manual review queue
- override analytics

### Phase 6: Monitoring and Governance

Scope:

- calibration drift
- feature drift
- model decay
- false-positive / false-negative tracking
- latency and fallback monitoring

Deliverables:

- score monitoring dashboard
- weekly evaluation report
- rollback playbook

## Online Scoring Flow

1. order created or rescored
2. raw source facts loaded
3. bootstrap refresh runs for platform-specific fields
4. online feature computation runs
5. feature schema version resolved
6. champion model selected per target
7. fraud and RTO scores generated
8. calibration artifact applied
9. decision policy applied
10. output persisted with all versions
11. operator-facing explanation returned

Fallback rule:

- if model artifact or required features are unavailable, use heuristic engine and persist `score_source=fallback`

## Offline Training Flow

1. snapshot labeled historical orders
2. materialize training feature set by schema version
3. split by time, not random only
4. train fraud and RTO models separately
5. evaluate discrimination and calibration
6. generate calibration artifacts
7. publish artifact and metrics
8. promote champion after approval

## Key Decisions

### Decision 1: Separate fraud and RTO models

Reason:

- fraud and RTO are related but not identical targets
- they have different labels and interventions
- explainability is better when targets stay separate

### Decision 2: Keep heuristics as fallback

Reason:

- scoring must remain available during provider, model, or schema failures
- operators need continuity during rollout

### Decision 3: Version everything

Versioned objects:

- model
- calibration
- feature schema
- decision policy

Reason:

- reproducibility
- safe rollback
- auditability

### Decision 4: Separate scoring from actioning

Reason:

- probability estimation and business policy evolve independently
- supports merchant customization

## Immediate Build Order

1. address validation provider integration
2. browser/device telemetry capture
3. feature schema and feature snapshot models
4. aggregate feature refresh jobs
5. calibration retraining job
6. fraud model training pipeline
7. RTO model training pipeline
8. champion/challenger serving
9. review queue and monitoring dashboards

## Risks

- insufficient label quality
- too few resolved outcomes for merchant-specific models
- frontend telemetry not deployed on all relevant pages
- provider cost and rate limits
- operator trust lost if explanations degrade

## Mitigations

- use global baseline model plus merchant-level recalibration first
- keep fallback heuristics
- capture raw factors and model explanations together
- start with shadow scoring before production decisions
- monitor approval, cancellation, and delivered-rate deltas after rollout

## Recommended Team Split

- backend platform: feature pipeline, model registry, scoring runtime
- frontend: telemetry collection and operator UI
- data/ML: training, calibration, evaluation
- ops/product: review policies, labeling, outcome hygiene

## Definition of Done For Industry-Scale v1

The platform is ready for industry-grade rollout when:

- device, IP, address, and shipment signals are all captured reliably
- every score stores model, feature, and calibration versions
- fraud and RTO probabilities are calibrated from historical outcomes
- challenger models can run in shadow mode
- operator actions and shipment outcomes feed back into labeling
- score drift and calibration drift are monitored continuously

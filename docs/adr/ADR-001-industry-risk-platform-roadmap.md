# ADR-001: Adopt A Versioned Hybrid Risk Platform

## Status

Accepted

## Context

The current risk engine is a rule-based system with staged enrichment and seeded calibration bands. It is useful for initial decision support, but it lacks the telemetry depth, feature reproducibility, model lifecycle controls, and operational monitoring expected from an industry-grade ecommerce risk platform.

The platform must support:

- fraud scoring
- COD/RTO scoring
- operator decisioning
- calibration and drift monitoring
- safe migration from heuristics to ML

## Decision

We will adopt a hybrid architecture with:

- separate fraud and RTO targets
- versioned feature schemas
- versioned model artifacts
- versioned calibration artifacts
- rules as fallback
- ML as the primary target-state scorer
- separate decision policy layer after scoring

## Why This Option

This option balances safety and ambition.

Advantages:

- preserves current production behavior during rollout
- enables reproducible offline training and online scoring
- supports champion/challenger experimentation
- allows merchant-specific policy tuning without retraining models
- improves auditability

Disadvantages:

- more moving parts than a pure rules engine
- requires new data capture and labeling discipline
- requires model monitoring investment

## Options Considered

### Option A: Keep expanding heuristic rules only

Rejected because:

- it will continue to saturate on sparse signals
- it does not scale well for dynamic fraud patterns
- it does not produce reliable probabilities

### Option B: Replace rules immediately with ML

Rejected because:

- labels and features are not mature enough
- operational risk is too high
- fallback coverage would be weak

### Option C: Hybrid transition with fallback heuristics

Accepted because:

- it is reversible
- it improves capability in stages
- it reduces rollout risk

## Consequences

Positive:

- industry-grade evolution path
- better explainability and audit trail
- safer model deployment

Negative:

- more schema and service complexity
- longer initial implementation window

## Implementation Consequences

Required new domains:

- telemetry
- feature schema and snapshots
- model registry
- calibration registry
- review and label management

Required invariants:

- every scored order stores feature, model, and calibration versions
- every training run is reproducible from stored feature snapshots
- online scoring always has a rules fallback path

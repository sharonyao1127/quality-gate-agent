# Project Metrics

This document captures public, reproducible signals for the reference implementation. It avoids customer data, private rule packs, and production-only tuning details.

## Current Public Test Signals

- Unit and workflow tests cover risk scoring, rule matching, negative keyword handling, traceability, schema validation, regression pack generation, web app behavior, and eval cases.
- Schema validation checks both output shape and semantic constraints, including risk level consistency, score ranges, and dimension keys.
- Idempotency coverage verifies that stable business output is deterministic for repeated analysis of the same input.

## Deterministic Output Contract

For the same input and same rule set, these fields should remain stable:

- Overall risk level.
- Overall risk score.
- Matched rule IDs.
- Match-level risk scores and risk levels.
- Matched keywords.
- Impacted areas.
- Suggested regression scope.
- Trace input hash and matched rule IDs.

These fields are intentionally runtime-specific and should not be compared for deterministic equality:

- Execution time.
- Timestamp.

## Public Demo Scope

The public rule set is intentionally small and sanitized. It demonstrates how the engine works without exposing production-grade domain rules.

Current demo risk areas:

- Idempotency.
- Async callback handling.
- Status consistency.
- API contract compatibility.
- Reconciliation.

## Commercial Boundary

Production engagements can add private metrics that are not included in this repository, such as:

- False positive rate by domain.
- Missed-risk review outcomes.
- Customer-specific rule coverage.
- Historical incident pattern coverage.
- CI adoption and review-time reduction.
- Domain-specific confidence thresholds.

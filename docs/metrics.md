# Project Metrics

This document captures public, reproducible signals for the reference implementation. It avoids customer data, private rule packs, and production-only tuning details.

## Current Public Test Signals

- Gate eval cases pass 3 / 3.
- AI PR review eval cases pass 1 / 1. The included case intentionally catches an AI-generated review that missed idempotency, async callback, and balance-consistency risks.
- The public classifier dataset contains 8 labeled samples.
- Unit and workflow tests cover risk scoring, rule matching, negative keyword handling, traceability, schema validation, regression pack generation, web app behavior, and eval cases.
- Schema validation checks both output shape and semantic constraints, including risk level consistency, score ranges, and dimension keys.
- Idempotency coverage verifies that stable business output is deterministic for repeated analysis of the same input.
- Confidence scoring flags low-certainty findings for human review using explainable rule-evidence heuristics.
- Keyword location traceability links matched evidence back to input line numbers.

## Current Public Classifier Baseline

Run:

```bash
python3 -m src.eval_framework
```

Current offline baseline:

| Classifier | Accuracy | Macro F1 | Samples |
|---|---:|---:|---:|
| keyword | 62.50% | 64.10% | 8 |
| hybrid | 62.50% | 64.10% | 8 |
| llm | 62.50% | 64.10% | 8 |

When `OPENAI_API_KEY` is not configured, `hybrid` and `llm` modes use the deterministic fallback path. That means the public offline comparison intentionally matches the keyword baseline. A model-enabled run should be reported separately with model name, token usage, latency, and date.

## Evidence Targets

By 2026-12-31, the target public evidence set is:

- 50 labeled risk samples.
- 20 sanitized PR-style case studies.
- Per-rule precision, recall, and F1 for keyword, hybrid, and LLM modes.
- Error analysis for false positives and missed risks.
- Human review correction tracking.
- Cost and P95 latency for model-assisted paths.

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
- Keyword line locations.
- Confidence score, level, review requirement, and reasons.

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

# Quality Gate Agent

AI-assisted quality gate for risky code, API, and OpenAPI changes.

This project turns change context into explainable risk scores, regression recommendations, traceable evidence, and PR-ready review comments. It is designed for complex B2B systems where a small change can affect payment reliability, ledger consistency, async callbacks, status flows, reconciliation, or customer-facing behavior.

This repository is a public reference implementation. Production-grade rule packs, domain adapters, customer workflows, and private evaluation sets are delivered separately in private engagements.

## What It Solves

Engineering teams often review risky changes with limited context. A diff may mention a new field, callback, retry, status, or API contract change, but the release risk is still judged manually.

Quality Gate Agent provides a lightweight workflow:

1. Load a git diff, API change note, or OpenAPI change summary.
2. Match the change against structured risk rules.
3. Calculate an explainable risk score.
4. Generate impacted areas and regression scope.
5. Export a Markdown report and PR comment.
6. Validate output shape and semantic constraints.
7. Preserve traceability for rule matches and scoring decisions.

## Best-Fit Use Cases

- Payment and ledger changes: idempotency, double deduction, refund consistency, reconciliation.
- Logistics and supply-chain workflows: status transitions, callback delays, inventory or route consistency.
- Ad platforms and retrieval systems: ranking/retrieval changes, contract drift, traffic-sensitive rollouts.
- Healthcare and EdTech SaaS: workflow stability, API compatibility, release risk review.
- Internal engineering tools: PR quality gates, regression recommendation, release readiness checks.

## Current Capabilities

- Structured YAML risk rules.
- Explainable risk scoring across business impact, data consistency, visibility, reversibility, and external dependency.
- Negative keyword handling to reduce false positives.
- Traceability report with input hash, matched rules, score calculation, and execution time.
- Pydantic schema validation with semantic constraints for risk level, score range, and dimension keys.
- Idempotency coverage for stable business outputs.
- Confidence assessment for low-certainty findings and human review routing.
- Markdown quality report and PR-ready comment output.
- Regression pack generation.
- Eval cases and pytest coverage.
- Optional FastAPI web UI for local demos.

## Demo Flow

```text
Git Diff / API Change / OpenAPI Summary
        |
        v
Change Loader
        |
        v
Gate Analyzer + Risk Rules
        |
        +--> Risk Score
        +--> Impacted Areas
        +--> Regression Scope
        +--> Traceability Report
        +--> Quality Gate Report
        +--> PR Comment
        +--> Eval Summary
```

## Example Output

```text
Overall Risk Level: HIGH
Overall Risk Score: 11 / 15
Rules Matched: 5
Traceability: input hash, matched rules, score calculation, execution time
```

Suggested regression scope can include:

- Submit duplicated requests with the same request ID.
- Simulate provider timeout and delayed callback.
- Verify balance is deducted only once.
- Validate frontend/backend status consistency.
- Check reconciliation behavior for provider response drift.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate reports:

```bash
python -m src.main
```

Run in strict CI gate mode:

```bash
python -m src.main --gate-mode strict
```

Run tests:

```bash
pytest -q
```

Start the local web UI:

```bash
uvicorn src.web_app:app --reload
```

Then open `http://127.0.0.1:8000`.

## Repository Structure

```text
examples/                 Sanitized input examples
risk_rules/               Public demo rule set
eval_cases/               Expected risk behavior cases
src/                      Analyzer, scoring, reports, traceability, validation
tests/                    Unit and workflow tests
docs/                     Architecture, roadmap, workflow notes
outputs/                  Generated local reports
```

## Public vs Private Boundary

This open-source version demonstrates the engine, interfaces, and engineering quality. It intentionally uses sanitized examples and generalized rules.

Private commercial work may include:

- Domain-specific payment, logistics, ad platform, healthcare, or EdTech rule packs.
- Customer-specific adapters for GitHub, CI, OpenAPI, incident systems, or test management tools.
- Private historical risk cases and evaluation sets.
- Rule weighting, false-positive tuning, and delivery playbooks.
- Hosted dashboards or internal workflow integrations.

See [Open Source Boundary](docs/open-source-boundary.md) for details.

## Quality Signals

Public metrics and deterministic-output expectations are tracked in [Project Metrics](docs/metrics.md).

## Roadmap

Near-term work focuses on production readiness:

- Human review gate workflow for ambiguous decisions.
- Keyword location traceability back to diff lines.
- GitHub PR comment workflow.
- Large PR chunking and risk aggregation.

See [Roadmap](docs/roadmap.md).

## Why This Project Exists

I built this as a practical bridge between QA engineering, AI-assisted development, and release risk control. My background spans payment platforms, ad systems, logistics workflows, healthcare SaaS, and EdTech systems, where quality work is not only about test execution but about understanding business risk early enough to change the release decision.

The core design principle is simple: use AI-era tooling to improve engineering speed, but keep the final risk signal explainable, testable, and auditable.

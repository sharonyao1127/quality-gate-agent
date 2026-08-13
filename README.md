# Quality Gate Agent

AI-assisted quality gate for risky code, API, OpenAPI, and PRD/business requirement changes.

This project turns change context into explainable risk scores, regression recommendations, traceable evidence, business-risk findings, and PR-ready review comments. It is designed for complex B2B systems where a small change can affect payment reliability, ledger consistency, async callbacks, status flows, reconciliation, rollout safety, or customer-facing behavior.

This repository also serves as a public reference implementation for **AI Quality / Agent Reliability / Evaluation Engineering** work. It demonstrates how to combine deterministic rules, structured LLM classification, labeled evaluation datasets, and LLM-as-a-Judge scoring into a single auditable quality gate.

Production-grade rule packs, domain adapters, customer workflows, and private evaluation sets are delivered separately in private engagements.

## What It Solves

Engineering teams often review risky changes with limited context. A diff may mention a new field, callback, retry, status, or API contract change, but the release risk is still judged manually.

Quality Gate Agent provides a lightweight workflow:

1. Load a git diff, API change note, OpenAPI change summary, PRD, or business requirement.
2. Normalize the input into a structured change context pack.
3. Match the change against code/API rules and business-risk rules.
4. Calculate explainable risk scores.
5. Validate output shape and semantic constraints.
6. Decide the gate action with risk and confidence signals.
7. Generate impacted areas, regression scope, reports, business-risk review, and PR comments.
8. Preserve traceability and audit steps for rule matches, model usage, and gate decisions.

## Best-Fit Use Cases

- Payment and ledger changes: idempotency, double deduction, refund consistency, reconciliation.
- Logistics and supply-chain workflows: status transitions, callback delays, inventory or route consistency.
- Ad platforms and retrieval systems: ranking/retrieval changes, contract drift, traffic-sensitive rollouts.
- Healthcare and EdTech SaaS: workflow stability, API compatibility, release risk review.
- Internal engineering tools: PR quality gates, regression recommendation, release readiness checks.

## Current Capabilities

### Core Quality Gate
- Structured YAML risk rules.
- Change Context Pack for normalized diff, API, OpenAPI, PRD, and business requirement inputs.
- Explainable risk scoring across business impact, data consistency, visibility, reversibility, and external dependency.
- Negative keyword handling to reduce false positives.
- Traceability report with input hash, matched rules, score calculation, and execution time.
- Keyword location traceability back to input line numbers.
- Pydantic schema validation with semantic constraints for risk level, score range, and dimension keys.
- Idempotency coverage for stable business outputs.
- Confidence assessment for low-certainty findings and human review routing.
- Markdown quality report and PR-ready comment output.
- Regression pack generation.
- Business-risk analyzer for PRD gaps, async callback ambiguity, payment reconciliation, state transitions, rollout safety, observability, and ownership.
- Eval cases and pytest coverage.
- Optional FastAPI web UI for local demos.

### AI-Native Layer
- **Hybrid risk classifier**: keyword rules + OpenAI-compatible LLM classification with structured output.
- **Classifier evaluation framework**: labeled dataset, per-rule precision/recall/F1, and macro-F1 comparison across keyword / hybrid / LLM modes.
- **LLM-as-a-Judge**: scores the helpfulness, actionability, and accuracy of generated reports using a separate LLM judge.
- **Agent workflow orchestration**: explicit analyze -> validate -> decide -> generate pipeline with audit steps.
- **Agent tool interface**: framework-agnostic Pydantic schemas and dispatcher for tool-based agent integration.
- **Gate decision layer**: maps risk and confidence into `pass`, `targeted_regression`, `human_review_required`, or `fail`.
- **Agent run observability**: captures run ID, step spans, durations, status, and decision metadata for audit and debugging.
- Graceful offline fallback: when no API key is configured, the system runs the keyword classifier and uses a deterministic mock judge for tests and demos.

## Demo Flow

```text
Git Diff / API Change / OpenAPI Summary / PRD
        |
        v
Change Loader + Context Pack
        |
        v
Gate Analyzer + Risk Rules + Business Risk Analyzer
        |
        +--> Risk Score
        +--> Business Risk Review
        +--> Impacted Areas
        +--> Regression Scope
        +--> Traceability Report
        +--> Agent Run Trace
        +--> Quality Gate Report
        +--> PR Comment
        +--> Eval Summary
```

For a guided walkthrough, see [Demo Script](docs/demo-script.md).

## AI Quality Architecture

```text
                  Git Diff / API Change / OpenAPI Summary
                                |
                                v
                    +-----------------------+
                    |   Change Loader       |
                    +-----------------------+
                                |
          +---------------------+---------------------+
          |                                           |
          v                                           v
+-------------------+                     +-------------------+
| Keyword Rules     |                     | LLM Classifier    |
| (deterministic)   |                     | (structured JSON) |
+-------------------+                     +-------------------+
          |                                           |
          +---------------------+---------------------+
                                |
                                v
                    +-----------------------+
                    |   Risk Merger         |
                    |   + Confidence        |
                    |   + Traceability      |
                    +-----------------------+
                                |
                                v
                    +-----------------------+
                    |   Gate Decision       |
                    | pass / review / fail  |
                    +-----------------------+
                                |
          +---------------------+---------------------+
          |                     |                     |
          v                     v                     v
   PR Comment           Quality Gate Report   Eval Framework
   (GitHub)             + Regression Pack     + LLM-as-a-Judge
```

This design lets you ship a deterministic gate today, then gradually introduce LLM classification, evaluation datasets, and judge scoring as you move into AI quality / agent reliability roles.

## Example Output

```text
Overall Risk Level: HIGH
Overall Risk Score: 11 / 15
Rules Matched: 5
Traceability: input hash, matched rules, score calculation, execution time
```

See [Demo Output](docs/demo-output.md) for a quick example of the generated report and PR comment shape.

Suggested regression scope can include:

- Submit duplicated requests with the same request ID.
- Simulate provider timeout and delayed callback.
- Verify balance is deducted only once.
- Validate frontend/backend status consistency.
- Check reconciliation behavior for provider response drift.

## GitHub PR Comment Workflow

When running against a GitHub PR, the agent creates or updates a single marker comment on the PR. The comment includes the overall risk level, matched rules, impacted areas, and recommended regression steps.

Example comment generated on [PR #13](https://github.com/sharonyao1127/quality-gate-agent/pull/13):

> ## Quality Gate Result: HIGH RISK
> **Risk Score:** 10 / 15
>
> ### Why this was flagged
> - **API Contract Compatibility Risk**: matched `required, openapi, contract`; score 10/15
> - **Async Callback Risk**: matched `timeout, callback, provider`; score 9/15
>
> ### Potentially impacted areas
> - API contract compatibility
> - backward compatibility
> - consumer integration
> - external provider callback
> - transaction final state
>
> ### Recommended before merge
> - Run API contract tests.
> - Simulate provider timeout.
> - Verify existing clients can parse the new response schema.
>
> ### Confidence
> - medium (70/100)
> - Human review required: no
>
> _Generated by Quality Gate Agent v0.2_

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate reports with the keyword classifier:

```bash
python3 -m src.main
```

Run with the hybrid classifier (requires `OPENAI_API_KEY`):

```bash
export OPENAI_API_KEY=sk-...
python3 -m src.main --classifier hybrid
```

Run with evaluation and LLM-as-a-Judge:

```bash
python3 -m src.main --eval
```

Use the agent tool interface from Python:

```python
from src.agent_tools import run_agent_tool

result = run_agent_tool(
    "analyze_change",
    {
        "change_text": "Provider callback timeout may update transaction status.",
        "input_type": "api_change",
        "business_domain": "payment",
    },
)
print(result["decision"]["action"])
```

Analyze a PRD or business requirement:

```bash
python3 -m src.main \
  --input examples/prd/payment_callback_prd.md \
  --input-type prd \
  --business-domain payment
```

Run in strict CI gate mode:

```bash
python3 -m src.main --gate-mode strict
```

Analyze a GitHub PR and post a comment:

```bash
export GITHUB_TOKEN=ghp_...
python3 -m src.main \
  --github-repository sharonyao1127/quality-gate-agent \
  --github-pr 13 \
  --publish-comment
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
examples/prd/             Sanitized PRD/business requirement examples
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

The repository also includes a GitHub Actions workflow that runs tests, generates quality gate outputs, and uploads generated reports as artifacts.

Generated local runs include `outputs/agent_run_trace.json` and `outputs/agent_run_trace.md`, which record the workflow spans, durations, status, and decision metadata for audit/debugging.

## Case Study

See [Payment Callback Risk Review](docs/case-study-payment-risk.md) for a sanitized example of how the gate supports payment release risk review.

## Roadmap

Recent work added the AI-native layer:

- [x] LLM-based risk classification with structured output.
- [x] Hybrid classifier combining keyword rules and LLM.
- [x] Classifier evaluation framework with precision/recall/F1.
- [x] LLM-as-a-Judge for report quality scoring.
- [x] GitHub PR comment workflow.

Near-term work focuses on production readiness:

- Human review gate workflow for ambiguous decisions.
- Large PR chunking and risk aggregation.
- Private evaluation dataset import and false-positive tuning.
- Cost/latency budget and model routing.

See [Roadmap](docs/roadmap.md).

## More Documentation

- [Architecture](docs/architecture.md)
- [Demo Script](docs/demo-script.md)
- [GitHub PR Comment Workflow](docs/github-pr-comment-workflow.md)
- [Agent Tool Interface](docs/agent-tool-interface.md)
- [Open Source Boundary](docs/open-source-boundary.md)

## Why This Project Exists

I built this as a practical bridge between QA engineering, AI-assisted development, and release risk control. My background spans payment platforms, ad systems, logistics workflows, healthcare SaaS, and EdTech systems, where quality work is not only about test execution but about understanding business risk early enough to change the release decision.

The project is also a deliberate portfolio piece for the AI quality / agent reliability transition. It shows hands-on experience with:

- LLM structured-output classification
- Agent workflow orchestration and gate decision modeling
- Labeled evaluation datasets and classifier metrics
- LLM-as-a-Judge output quality scoring
- CI/CD integration and traceability
- Agent run tracing and audit-friendly workflow metadata
- Pydantic schema validation and deterministic fallbacks

The core design principle is simple: use AI-era tooling to improve engineering speed, but keep the final risk signal explainable, testable, and auditable.

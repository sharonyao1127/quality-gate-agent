# Quality Gate Agent

Quality Gate Agent is a change-aware QA engineering prototype that maps git diffs, API changes, and OpenAPI change summaries to explainable risk scores, impacted areas, regression scope, and PR-ready quality gate comments.

It explores how QA can shift left from late-stage regression execution to earlier change risk assessment in CI / code review workflows.

It demonstrates how a QA / Test Development Engineer can shift testing left by turning change context into:

- risk score
- impacted areas
- regression scope
- PR comment report
- eval-based quality checks

## Why I Built This

In fast-moving product teams, QA engineers often receive late-stage changes with limited context. A small code or API change may affect payment reliability, state consistency, idempotency, asynchronous callbacks, reconciliation, user-facing status, or regression scope.

This project explores a practical quality gate workflow:

1. Read a git diff, API change note, or OpenAPI change summary.
2. Match changes against structured quality risk rules.
3. Calculate explainable risk score.
4. Generate impacted areas and regression suggestions.
5. Produce a Markdown quality gate report.
6. Produce a PR comment that can be used in CI / code review workflows.
7. Evaluate the agent output against expected risk cases.

This repository contains only generalized and sanitized examples. It does not include company-specific business logic, internal APIs, production data, or confidential implementation details.

---

## What Makes v0.2 Better Than a Simple Demo

This version includes:

- **Risk scoring model** instead of only `high / medium / low` keyword tags
- **PR comment format output** for real code review workflows
- **Eval cases** to check whether the agent detects expected risk areas
- **OpenAPI change example** to simulate API contract risk
- **GitHub Actions** for report generation and tests
- **Sanitized fintech-style examples** without exposing internal business details
- **AI-generated PR review eval** to detect missing critical risks
- **Structured regression pack output** (`outputs/regression_pack.yaml`)
- **CI gate mode** (`--gate-mode strict`) to fail builds on high-risk changes

---

## Demo Flow

```text
Git Diff / API Change / OpenAPI Change Summary
        |
        v
Quality Gate Rules
        |
        v
Risk Analyzer
        |
        +--> Risk Score
        +--> Impacted Areas
        +--> Regression Scope
        +--> Quality Gate Report
        +--> PR Comment
        +--> Eval Checks
```

---

## Project Structure

```text
quality-gate-agent-v0.2/
├── examples/
│   ├── diffs/
│   │   └── payment_status_change.diff
│   ├── api_changes/
│   │   └── payment_api_change.md
│   └── openapi/
│       ├── old_payment_api.yaml
│       ├── new_payment_api.yaml
│       └── openapi_change_summary.md
├── risk_rules/
│   └── quality_gate_rules.yaml
├── eval_cases/
│   ├── high_risk_async_callback.yaml
│   ├── medium_risk_status_change.yaml
│   └── low_risk_copy_change.yaml
├── src/
│   ├── main.py
│   ├── change_loader.py
│   ├── gate_analyzer.py
│   ├── risk_scoring.py
│   ├── report_generator.py
│   ├── pr_comment_generator.py
│   └── eval_runner.py
├── tests/
│   ├── test_gate_analyzer.py
│   ├── test_risk_scoring.py
│   └── test_eval_cases.py
├── outputs/
│   ├── quality_gate_report.md
│   ├── pr_comment.md
│   └── eval_summary.md
├── docs/
│   ├── architecture.md
│   ├── risk_model.md
│   └── roadmap.md
└── .github/workflows/
    └── test.yml
```

---

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

If overall risk score is `>= 10`, the process exits non-zero with:

```text
Quality gate failed: high-risk change requires manual review.
```

Run tests:

```bash
pytest -q
```

Run eval cases manually:

```bash
python -m src.eval_runner
```

---

## Example Output

### Quality Gate Result

```text
Overall Risk Level: HIGH
Risk Score: 13 / 15
```

### Impacted Areas

```text
- idempotency
- balance consistency
- external provider callback
- transaction status consistency
- reconciliation
```

### Suggested Regression Scope

```text
- Submit duplicated request with same request ID.
- Simulate provider timeout.
- Simulate delayed success callback.
- Verify balance is deducted only once.
- Verify frontend/backend status display.
```

---

## Example PR Comment

```markdown
## Quality Gate Result: HIGH RISK

Risk Score: 13 / 15

This change may impact:
- idempotency
- external provider callback
- transaction status consistency

Recommended before merge:
- run duplicate request regression
- verify delayed callback handling
- check frontend/backend status consistency
```

---

## Tech Stack

Python · FastAPI · HTML · Pytest · YAML · GitHub Actions · Risk-based Testing · QA Automation · CI Quality Gate

## Web UI (New)

Start local UI:

```bash
uvicorn src.web_app:app --reload
```

Then open `http://127.0.0.1:8000` and:

1. Input API change summary
2. Click Analyze
3. Get Risk Score / Impacted Areas / PR Comment

This helps position the project as:

- AI-powered engineering tools
- Lightweight full-stack internal tools
- Developer productivity workflows

---

## Current Status

v0.2 prototype. Current implementation uses structured rules and explainable scoring. Future versions can integrate LLM-based change summarization, OpenAPI diff automation, GitHub PR comments, and CI merge gates.

## Demo Output

After running:

```bash
python3 -m src.main
python3 -m src.eval_runner
pytest -q
```

The agent generates:

- `outputs/quality_gate_report.md`
- `outputs/pr_comment.md`
- `outputs/eval_summary.md`

Example result:

```text
Overall Risk Level: HIGH
Overall Risk Score: 13 / 15
Passed Eval Cases: 3 / 3
```

## Key Capabilities

- Reads git diff, API change notes, and OpenAPI change summaries.
- Matches changes against structured quality risk rules.
- Calculates explainable risk scores.
- Generates impacted areas and suggested regression scope.
- Produces PR-ready quality gate comments.
- Uses eval cases to validate whether the gate produces expected risk levels.

## Interview Talking Points

I built this project to explore how QA can shift left in fast-moving engineering teams.

Instead of manually deciding regression scope at the end of development, this prototype reads change context such as git diffs, API changes, and OpenAPI summaries, then maps them to structured risk rules.

The v0.2 version includes an explainable risk scoring model, PR comment output, and eval cases. The eval layer helped expose false positives in low-risk changes, which shows that quality gates should be evaluated, not just generated.

This project demonstrates my interest in QA automation, risk-based testing, CI quality gates, and AI-era quality engineering workflows.

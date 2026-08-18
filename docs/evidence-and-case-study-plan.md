# Evidence and Case Study Plan

Quality Gate Agent is being developed as a hero product for AI quality, release-risk control, and complex B2B workflow review. The goal is not to add more agents. The goal is to make release-risk judgment more measurable, auditable, and useful in real engineering workflows.

## Product Thesis

Quality Gate Agent answers this question:

> Can an AI-assisted quality gate help engineering teams make better release decisions for risky software changes?

The system should earn trust through evidence:

- labeled cases
- baseline comparisons
- traceable rule matches
- human review corrections
- reproducible metrics
- clear error analysis

## Closed Loop

The target workflow is:

```text
Real or sanitized PR
        |
        v
Quality Gate Agent analysis
        |
        +--> risk decision
        +--> impacted areas
        +--> regression recommendation
        +--> PR comment
        +--> traceability evidence
        |
        v
Human review confirms or corrects the result
        |
        v
Correction becomes a labeled eval case
        |
        v
Dataset, rules, prompt, or routing logic improves
```

This loop is more valuable than adding unrelated features because it turns the repository from an AI demo into an engineering experiment.

## Current Public Evidence

As of the current public repository:

- 8 labeled classifier samples in `eval_dataset/risk_samples.yaml`.
- 3 deterministic gate eval cases in `eval_cases/`.
- 1 AI PR review quality eval case in `eval_cases/ai_pr_review/`.
- Keyword, hybrid, and LLM classifier comparison report generation.
- LLM-as-a-Judge report scoring with deterministic mock fallback.
- GitHub Actions workflow for tests, eval cases, report artifacts, and PR comments.

Current public classifier baseline without an API key:

| Dataset | Mode | Accuracy | Macro F1 | Samples |
|---|---|---:|---:|---:|
| Public labeled risk samples | keyword | 62.50% | 64.10% | 8 |
| Public labeled risk samples | hybrid fallback | 62.50% | 64.10% | 8 |
| Public labeled risk samples | llm fallback | 62.50% | 64.10% | 8 |

Hybrid and LLM modes use deterministic fallback when `OPENAI_API_KEY` is not configured, so the public offline result is intentionally identical.

## 2026-12-31 Evidence Targets

- 50 labeled risk cases covering payment, async callbacks, API contracts, reconciliation, status consistency, ads, logistics, healthcare SaaS, and EdTech SaaS.
- 20 sanitized PR-style case studies with input, agent output, human review note, and resulting eval change.
- Baseline comparison across keyword, hybrid, and LLM modes with precision, recall, F1, and error analysis.
- Cost and latency tracking for model-assisted paths.
- A short demo recording or GIF showing PR analysis, risk decision, regression recommendation, and PR comment.

## Case Study Template

See `docs/case-study-template.md` for a reusable fill-in template.

Each strong case study should include:

- **Scenario:** what changed and why it matters.
- **Risk pattern:** idempotency, callback ordering, reconciliation, contract compatibility, rollout, observability, ownership, or workflow consistency.
- **Agent output:** matched rules, risk score, confidence, impacted areas, regression scope, traceability.
- **Human correction:** what a reviewer confirmed, removed, or added.
- **Eval update:** the labeled sample or rule adjustment created from the review.
- **Result:** whether the change improved recall, reduced false positives, clarified routing, or improved reviewer usefulness.

## Boundaries

Only sanitized and generalized patterns belong in this repository. Company code, internal APIs, customer data, incident details, private rules, and proprietary workflows should stay out of the public project.

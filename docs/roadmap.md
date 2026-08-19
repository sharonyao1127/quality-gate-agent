# Roadmap

The roadmap is intentionally narrow. Quality Gate Agent is the hero project, so the next phase focuses on proof: demo quality, labeled evidence, PR-review feedback loops, and error analysis.

## v0.2 Completed

- [x] Git diff input
- [x] API change note input
- [x] OpenAPI change summary input
- [x] Structured quality gate rules
- [x] Risk scoring model
- [x] Overall risk level calculation
- [x] Quality gate report
- [x] PR comment output
- [x] Eval cases
- [x] Pytest tests
- [x] GitHub Actions workflow

## v0.3 In Progress

- [x] Traceability report for rule matches and score calculation
- [x] Output schema validation
- [x] Semantic constraints for risk levels, score ranges, and dimension keys
- [x] Idempotency tests for deterministic output
- [x] Agent decision evals for gate action, review routing, and high-risk recall
- [x] Confidence scorer for low-certainty findings
- [x] Keyword location traceability back to input lines
- [x] Agent workflow orchestration
- [x] Gate decision layer for pass, targeted regression, human review, and strict failure
- [x] Human review gate for ambiguous risk decisions
- [x] Change Context Pack for PRD/business requirement inputs
- [x] Business risk analyzer for requirements, callback gaps, reconciliation, rollout, and ownership
- [x] Knowledge Store Lite for reusable payment, ads, and logistics risk patterns
- [x] Agent tool interface with Pydantic schemas and dispatcher
- [x] Agent run trace with step spans, durations, and workflow status
- [x] GitHub Actions workflow for tests and report artifacts

## v0.4 Evidence Loop

- [ ] Expand public labeled classifier dataset from 8 to 50 sanitized risk cases
- [ ] Add 20 sanitized PR-style case studies
- [x] Add human review correction notes to case studies *(Week 5 scaffolding: `eval_dataset/human_corrections/`, schema for `label_correction` / `missed_risk` / `false_positive`)*
- [x] Convert human corrections into eval samples *(Week 5: `collect_new_samples_from_corrections` plus first Problem-Lab sample `problem_lab_001_payment_rollback_race`)*
- [ ] Add false-positive and missed-risk error analysis *(Week 5: schema ready, surface area in `outputs/evidence_loop_report.md` only — full error-analysis doc pending)*
- [ ] Track model-assisted cost, token usage, and latency in eval reports
- [ ] Add module ownership mapping for regression recommendation
- [ ] Add large PR chunking and risk aggregation
- [ ] Add CI failure threshold for high-risk or low-confidence changes

## v0.5 Closed-Loop Evidence (Week 5 scaffolding)

The baseline-vs-post-correction pipeline is now live. Adding one real-work
sample measurably shifted accuracy on both runtimes:

| Runtime | Level Acc Δ | Decision Acc Δ | Sample Δ |
|---|---:|---:|---:|
| Native | +4.2% | +5.6% | +1 |
| LangGraph | +4.2% | +5.6% | +1 |

What landed:

- `src/human_review.py` — three-type correction dataclass + loader + applier.
- `eval_dataset/human_corrections/problem_lab_001_payment_rollback_race.yaml` — first Problem-Lab sample referencing a sanitized real-work incident.
- `src/runtime_eval.py` — `run_evidence_loop_eval()` and `generate_evidence_loop_report()` now run on every invocation of `python3 -m src.runtime_eval`; report at `outputs/evidence_loop_report.md`.
- `tests/test_human_review.py` + extended `tests/test_runtime_eval.py` — 12 new tests, total suite 134 passed.

What still needs growth: more Problem-Lab samples (target 50 by 2026-12-31), case-study write-ups using the corrections, and a public visualization of the per-correction deltas.

## Deferred Feature Ideas

These are useful, but lower priority than evidence quality:

- [ ] Automated OpenAPI diff parser
- [ ] Vector/RAG retrieval for private historical risk patterns
- [ ] LLM-based change summary
- [ ] MCP/tool interface for agent workflow integration
- [ ] Dashboard-style HTML report

## Commercial Packaging

- [ ] Add a short demo GIF or terminal recording
- [x] Add a payment change case study
- [x] Add public metrics for runtime, eval coverage, and rule coverage
- [x] Add demo script for README/client walkthroughs
- [ ] Keep production-grade rule packs and customer adapters private

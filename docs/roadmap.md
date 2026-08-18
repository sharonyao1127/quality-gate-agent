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
- [ ] Add human review correction notes to case studies
- [ ] Convert human corrections into eval samples
- [ ] Add false-positive and missed-risk error analysis
- [ ] Track model-assisted cost, token usage, and latency in eval reports
- [ ] Add module ownership mapping for regression recommendation
- [ ] Add large PR chunking and risk aggregation
- [ ] Add CI failure threshold for high-risk or low-confidence changes

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

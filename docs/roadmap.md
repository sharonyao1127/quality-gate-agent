# Roadmap

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
- [x] Confidence scorer for low-certainty findings
- [x] Keyword location traceability back to input lines
- [x] Agent workflow orchestration
- [x] Gate decision layer for pass, targeted regression, human review, and strict failure
- [x] Human review gate for ambiguous risk decisions
- [x] Change Context Pack for PRD/business requirement inputs
- [x] Business risk analyzer for requirements, callback gaps, reconciliation, rollout, and ownership
- [x] GitHub Actions workflow for tests and report artifacts

## v0.4 Candidate

- [ ] Add automated OpenAPI diff parser
- [ ] Add GitHub PR comment posting workflow
- [ ] Add module ownership mapping
- [ ] Add local knowledge store for reusable risk patterns
- [ ] Add LLM-based change summary
- [ ] Add MCP/tool interface for agent workflow integration
- [ ] Generate regression checklist by module
- [ ] Add CI failure threshold for high-risk changes
- [ ] Add dashboard-style HTML report

## Commercial Packaging

- [ ] Add a short demo GIF or terminal recording
- [x] Add a payment change case study
- [x] Add public metrics for runtime, eval coverage, and rule coverage
- [x] Add demo script for README/client walkthroughs
- [ ] Keep production-grade rule packs and customer adapters private

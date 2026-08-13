# Architecture

Quality Gate Agent is a reference implementation for explainable release-risk review and agent reliability engineering. It keeps the core decision path deterministic and auditable while allowing optional LLM classification and judge evaluation.

## Current Architecture

```text
Git Diff / API Note / OpenAPI Summary / PRD / GitHub PR Diff
        |
        v
Agent Workflow Orchestrator
        |
        +--> Load Change Context
        +--> Build Context Pack
        +--> Retrieve Risk Knowledge
        +--> Review Business Risk
        +--> Classify Risk
        +--> Validate Schema
        +--> Decide Gate
        +--> Generate Outputs
        |
        v
Gate Analyzer + Optional LLM Classifier
        |
        +--> Matched Rules
        +--> Risk Score
        +--> Confidence Assessment
        +--> Keyword Line Locations
        |
        v
Result Validators
        |
        +--> Schema Validation
        +--> Semantic Constraints
        +--> Idempotency Coverage
        |
        v
Gate Decision
        |
        +--> pass
        +--> targeted_regression
        +--> human_review_required
        +--> fail
        |
        v
Outputs
        |
        +--> Quality Gate Report
        +--> PR Comment
        +--> Traceability Report
        +--> Regression Pack
        +--> Eval Summary
        +--> Audit Steps
```

## Core Modules

- `src/change_loader.py`: loads sanitized example inputs for local runs.
- `src/context_pack.py`: normalizes change text, PRDs, and business requirements into a structured context pack.
- `src/knowledge_store.py`: loads and retrieves reusable local risk patterns for domain-aware context.
- `src/business_risk_analyzer.py`: flags PRD and business-risk gaps such as missing acceptance criteria, callback ambiguity, reconciliation gaps, rollout risk, and ownership gaps.
- `src/agent_workflow.py`: orchestrates the analyze, validate, decide, and generate workflow.
- `src/gate_analyzer.py`: matches change text against risk rules and produces risk findings.
- `src/gate_decision.py`: maps risk and confidence into an explicit gate action.
- `src/risk_scoring.py`: calculates risk levels and score thresholds.
- `src/confidence_scorer.py`: estimates confidence and routes low-certainty findings to human review.
- `src/traceability.py`: records rule matches, score calculations, keyword line locations, and exportable traces.
- `src/schema_validator.py`: validates output shape and semantic consistency.
- `src/report_generator.py`: produces the Markdown quality gate report.
- `src/pr_comment_generator.py`: formats PR-ready review comments.
- `src/regression_pack_generator.py`: builds a structured regression checklist.
- `src/eval_runner.py`: runs public eval cases against expected risk behavior.

## Design Principles

- Explainability first: every risk output should connect back to matched rules, keywords, scores, and input lines.
- Deterministic core: structured rules and schema validation keep the main gate stable and testable.
- Knowledge reuse: local risk patterns make historical domain expertise explicit without exposing private customer data.
- Explicit decisions: final gate actions are represented as structured data, not hidden inside report prose.
- Human review friendly: confidence assessment marks findings that need manual inspection.
- Context-aware inputs: requirements and PRDs are reviewed before implementation, not only after code exists.
- Open-core boundary: public examples demonstrate the workflow; production rule packs and adapters stay private.

## Future Extensions

- GitHub PR comment automation.
- Large PR chunking and risk aggregation.
- Module ownership mapping.
- OpenAPI diff automation.
- Optional LLM summarization with structured output validation.
- Vector/RAG retrieval for private historical risk patterns and incident-derived checks.
- MCP/tool interface for agent workflow integration.

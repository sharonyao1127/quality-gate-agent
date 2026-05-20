# Architecture

Quality Gate Agent is a reference implementation for explainable release-risk review. It keeps the core decision path deterministic and auditable, while leaving room for future AI-assisted summarization and workflow integration.

## Current Architecture

```text
Git Diff / API Note / OpenAPI Summary
        |
        v
Change Loader
        |
        v
Structured Risk Rules
        |
        v
Gate Analyzer
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
Outputs
        |
        +--> Quality Gate Report
        +--> PR Comment
        +--> Traceability Report
        +--> Regression Pack
        +--> Eval Summary
```

## Core Modules

- `src/change_loader.py`: loads sanitized example inputs for local runs.
- `src/gate_analyzer.py`: matches change text against risk rules and produces risk findings.
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
- Human review friendly: confidence assessment marks findings that need manual inspection.
- Open-core boundary: public examples demonstrate the workflow; production rule packs and adapters stay private.

## Future Extensions

- GitHub PR comment automation.
- Large PR chunking and risk aggregation.
- Module ownership mapping.
- OpenAPI diff automation.
- Optional LLM summarization with structured output validation.

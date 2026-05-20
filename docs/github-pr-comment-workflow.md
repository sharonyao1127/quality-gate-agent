# GitHub PR Comment Workflow

This document describes the intended GitHub integration path for Quality Gate Agent.

## Current Public Workflow

The repository currently supports local generation of:

- `outputs/quality_gate_report.md`
- `outputs/pr_comment.md`
- `outputs/traceability_report.md`
- `outputs/regression_pack.yaml`

The CI workflow can run tests and generate these reports as artifacts.

## Target PR Workflow

```text
Pull Request Opened
        |
        v
Collect Diff / API Notes / OpenAPI Summary
        |
        v
Run Quality Gate Agent
        |
        +--> Generate Risk Report
        +--> Generate Traceability Report
        +--> Generate PR Comment
        |
        v
Post Comment To Pull Request
        |
        v
Require Human Review For High Risk Or Low Confidence
```

## PR Comment Contents

A production PR comment should include:

- overall risk level and score
- confidence assessment
- matched rule summary
- impacted areas
- suggested regression scope
- traceability report link
- explicit human review requirement when needed

## Integration Notes

- Public demo rules are intentionally sanitized.
- Production workflows should load customer-specific rule packs from private storage.
- Posting comments requires GitHub token permissions.
- High-risk or low-confidence findings can be used as branch protection signals.

## Next Implementation Step

Add a GitHub Action that:

1. installs dependencies
2. runs tests
3. runs `python -m src.main`
4. uploads generated reports as artifacts
5. optionally posts `outputs/pr_comment.md` to the PR

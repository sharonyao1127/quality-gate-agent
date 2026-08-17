# GitHub PR Comment Workflow

This document describes the GitHub integration path for Quality Gate Agent.

## Current Public Workflow

The repository supports local generation of:

- `outputs/quality_gate_report.md`
- `outputs/pr_comment.md`
- `outputs/traceability_report.md`
- `outputs/regression_pack.yaml`

The GitHub Actions workflow can:

- run tests
- run eval cases
- generate quality gate reports as artifacts
- analyze pull requests from the same repository
- create or update the marker PR comment when `GITHUB_TOKEN` permissions are available

## PR Workflow

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
        |
        v
Reviewer Confirms Or Corrects The Finding
        |
        v
Correction Becomes A Labeled Eval Case
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

## Next Evidence Step

The next step is to preserve reviewer feedback as structured evidence:

1. save sanitized PR input
2. save generated risk decision and comment
3. record human confirmation or correction
4. convert the correction into an eval sample
5. track whether the rule, classifier, or routing logic improved

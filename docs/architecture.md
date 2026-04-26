# Architecture

## v0.2 Architecture

```text
Git Diff / API Change / OpenAPI Change Summary
        |
        v
Quality Gate Rules
        |
        v
Gate Analyzer
        |
        +--> Risk Score
        |
        +--> Impacted Areas
        |
        +--> Suggested Regression Scope
        |
        +--> Quality Gate Report
        |
        +--> PR Comment
        |
        +--> Eval Summary
```

## Design Notes

The v0.2 version uses structured rules and explainable scoring.

The design intentionally avoids hidden decisions. Each risk output should be traceable to:

- matched keywords
- risk dimensions
- impacted areas
- suggested regression items

Future versions can integrate LLMs for change summarization while keeping scoring and evaluation transparent.

# Demo Output

This page shows the kind of output Quality Gate Agent produces from the sanitized public examples. It is intended for quick review without running the project locally.

## Quality Gate Summary

```text
Overall Risk Level: HIGH
Overall Risk Score: 13 / 15
Rules Matched: 5
Confidence: high (95/100)
Human Review Required: no
```

## Matched Risk Rules

| Rule | Level | Score | Example Matched Keywords |
|---|---|---:|---|
| Idempotency Risk | high | 11 | retry, duplicate, request_id, balance, deduct |
| Async Callback Risk | high | 13 | timeout, callback, delayed, provider |
| Status Consistency Risk | medium | 8 | status, frontend, backend, enum |
| API Contract Compatibility Risk | high | 10 | required, openapi, contract, response field |
| Reconciliation Risk | high | 11 | reconciliation, confirmation, transaction |

## Impacted Areas

- API contract compatibility
- balance consistency
- external provider callback
- frontend/backend consistency
- idempotency
- reconciliation
- transaction final state
- user-facing status display

## Suggested Regression Scope

- Submit duplicated request with same request ID.
- Submit duplicated request with same transaction ID.
- Simulate provider timeout.
- Simulate delayed success callback.
- Simulate duplicated callback.
- Verify balance is deducted only once.
- Verify final transaction state cannot be overwritten incorrectly.
- Verify frontend display for each backend status.
- Verify reconciliation report for long-pending transactions.
- Run API contract tests.

## PR Comment Shape

```markdown
## Quality Gate Result: HIGH RISK

**Risk Score:** 13 / 15

### Why this was flagged

- **Idempotency Risk**: matched `retry, duplicate, request_id, balance, deduct`; score 11/15
- **Async Callback Risk**: matched `timeout, callback, delayed, provider`; score 13/15

### Confidence

- high (95/100)
- Human review required: no
```

## Traceability Shape

Traceability output includes:

- input hash
- input type
- ruleset version
- total rules evaluated
- matched rule IDs
- keyword locations by input line
- score calculation details
- execution time and timestamp

Runtime-specific fields such as execution time and timestamp are intentionally not part of deterministic equality checks.

## Notes

The public demo output uses sanitized examples and generalized rules. Production engagements can add private rule packs, customer adapters, domain-specific thresholds, and customer-specific report formats.

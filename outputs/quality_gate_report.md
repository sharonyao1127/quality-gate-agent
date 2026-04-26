# Quality Gate Report

## Overall Risk Level: HIGH

## Overall Risk Score: 13 / 15

## Matched Risk Rules

| Rule | Level | Score | Matched Keywords |
|---|---|---:|---|
| Idempotency Risk | high | 11 | retry, duplicate, request_id, balance, deduct |
| Async Callback Risk | high | 13 | timeout, callback, delayed, provider, pending_confirmation, waiting_callback, callback_required |
| Status Consistency Risk | medium | 8 | status, frontend, backend, display, pending, enum |
| API Contract Compatibility Risk | high | 10 | required, openapi, contract, enum, response field, provider_request_id |
| Reconciliation Risk | high | 11 | reconciliation, confirmation, transaction, provider_response, provider request |

## Risk Dimensions

### Idempotency Risk
- business_impact: 3
- data_consistency: 3
- user_visibility: 2
- reversibility: 2
- external_dependency: 1

### Async Callback Risk
- business_impact: 3
- data_consistency: 3
- user_visibility: 2
- reversibility: 2
- external_dependency: 3

### Status Consistency Risk
- business_impact: 2
- data_consistency: 1
- user_visibility: 2
- reversibility: 2
- external_dependency: 1

### API Contract Compatibility Risk
- business_impact: 2
- data_consistency: 2
- user_visibility: 2
- reversibility: 2
- external_dependency: 2

### Reconciliation Risk
- business_impact: 3
- data_consistency: 3
- user_visibility: 1
- reversibility: 2
- external_dependency: 2


## Impacted Areas

- API contract compatibility
- backward compatibility
- balance consistency
- client compatibility
- consumer integration
- external provider callback
- frontend/backend consistency
- idempotency
- provider confirmation
- reconciliation
- state machine
- timeout handling
- transaction consistency
- transaction final state
- transaction record uniqueness
- user-facing status display

## Suggested Regression Scope

- Run API contract tests.
- Simulate delayed success callback.
- Simulate duplicated callback.
- Simulate provider timeout.
- Submit duplicated request with same request ID.
- Submit duplicated request with same transaction ID.
- Verify balance is deducted only once.
- Verify clients can handle newly added status values.
- Verify completed status transition.
- Verify enum compatibility with older clients.
- Verify existing clients can parse the new response schema.
- Verify failed status transition.
- Verify final transaction state cannot be overwritten incorrectly.
- Verify frontend display for each backend status.
- Verify missing provider confirmation handling.
- Verify missing required field behavior.
- Verify only one transaction record is created.
- Verify pending status transition.
- Verify reconciliation report for long-pending transactions.
- Verify request/confirmation mismatch detection.

## Gate Recommendation

High-risk change detected. Regression scope should be reviewed before merge/release.
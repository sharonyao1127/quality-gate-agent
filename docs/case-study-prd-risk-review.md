# Case Study: PRD Business Risk Review

This case study shows how Quality Gate Agent can review a product or business requirement before code is written.

The goal is not to replace product, engineering, or QA judgment. The goal is to make hidden release-risk gaps visible early enough that teams can turn them into acceptance criteria, regression cases, rollout tasks, and owner sign-offs.

## Input

Example file:

```bash
examples/prd/payment_callback_prd.md
```

Run:

```bash
python3 -m src.main \
  --input examples/prd/payment_callback_prd.md \
  --input-type prd \
  --business-domain payment
```

## What The Agent Checks

- Missing acceptance criteria.
- Async callback, timeout, retry, and idempotency gaps.
- Payment reconciliation or ledger consistency gaps.
- Ambiguous state transitions and terminal states.
- Rollout, observability, alerting, and rollback gaps.
- Missing ownership for external dependencies.

## Example Findings

For the sample PRD, the agent should flag risks such as:

- Provider callback behavior exists, but timeout/retry/idempotency behavior is incomplete.
- Payment transaction behavior exists, but reconciliation or ledger-audit requirements are not explicit.
- Pending/completed/failed statuses are mentioned, but state transitions are not fully specified.
- Rollout is mentioned, but monitoring, alerting, feature flag, and rollback details are incomplete.

## Why This Matters

In complex B2B systems, many production incidents come from context gaps rather than code syntax errors. A change can pass unit tests while still being risky because the PRD did not specify callback ordering, retry semantics, reconciliation, old-client compatibility, or rollback triggers.

This module turns those gaps into explicit review items before implementation starts.

## Public vs Private Boundary

The public repository includes generic, sanitized business-risk rules and examples.

Private customer engagements can add:

- Domain-specific risk patterns.
- Internal incident-derived examples.
- Ownership maps.
- Private eval sets.
- Connectors for PRDs, tickets, knowledge bases, and release systems.

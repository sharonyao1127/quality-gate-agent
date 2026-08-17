# Case Study Template

Use this template when turning a real engineering change into a sanitized public case study. Keep the business pattern, remove company-specific details.

## Scenario

Describe the change in neutral terms:

- system area
- change type
- user or downstream impact
- why the release decision is non-trivial

## Sanitized Input

Include the PR summary, diff excerpt, API note, OpenAPI summary, PRD excerpt, or business requirement text after removing confidential details.

## Expected Risk Pattern

Name the core pattern:

- idempotency
- async callback ordering
- balance or ledger consistency
- reconciliation
- API contract compatibility
- status consistency
- rollout safety
- observability
- ownership ambiguity

## Agent Output

Capture:

- overall risk level and score
- matched rules
- confidence level
- impacted areas
- suggested regression scope
- traceability evidence
- PR comment summary

## Human Review Note

Record what a reviewer changed:

- confirmed finding
- removed false positive
- added missed risk
- adjusted severity
- added required regression

## Eval Update

State how the case improved the system:

- new labeled sample
- rule keyword update
- negative keyword update
- prompt or schema update
- routing or confidence-threshold update

## Result

Summarize the measurable effect:

- recall improvement
- false-positive reduction
- clearer human-review routing
- better regression recommendation
- cost or latency observation

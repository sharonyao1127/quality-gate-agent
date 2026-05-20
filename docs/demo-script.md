# Demo Script

Use this script for a short GitHub README demo, a terminal recording, or a client walkthrough.

## Goal

Show how Quality Gate Agent turns a risky payment/API change into:

- explainable risk score
- matched rules and keywords
- confidence assessment
- suggested regression scope
- traceability report
- PR-ready comment

## Setup

```bash
pip install -r requirements.txt
```

## Run The Demo

Generate all public demo outputs:

```bash
python3 -m src.main
```

Run the focused validation set:

```bash
pytest tests/test_gate_analyzer.py tests/test_traceability.py tests/test_confidence_scorer.py tests/test_schema_validator.py tests/test_idempotency.py -q
```

Optional strict gate mode:

```bash
python3 -m src.main --gate-mode strict
```

## Walkthrough

1. Start with the input examples in `examples/`.
2. Show the public demo rules in `risk_rules/quality_gate_rules.yaml`.
3. Run `python3 -m src.main`.
4. Open `outputs/quality_gate_report.md`.
5. Point out the overall risk score and matched rules.
6. Show confidence assessment and human review routing.
7. Open `outputs/traceability_report.md`.
8. Point out keyword locations and line-level evidence.
9. Open `outputs/pr_comment.md`.
10. Explain how this can become a CI/PR workflow.

## Suggested Narration

```text
This demo simulates a payment-related change touching retries, provider callbacks, status updates, and reconciliation.

The gate maps the change to structured risk rules, calculates an explainable score, recommends regression scope, and exports traceability evidence.

The public repository uses sanitized examples. Production engagements can add private rule packs, customer adapters, and CI workflows.
```

## What To Emphasize

- This is not a generic chatbot review.
- The core risk signal is deterministic and testable.
- Traceability shows why a rule matched.
- Confidence scoring helps decide when human review is needed.
- The public repo demonstrates the engine; domain intelligence can remain private.

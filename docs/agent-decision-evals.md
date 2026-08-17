# Agent Decision Evals

Quality Gate Agent evaluates both classifier behavior and final gate decisions.

Classifier metrics answer:

- Did the analyzer detect the expected risk rules?
- Did it predict the expected overall risk level?
- What are the per-rule precision, recall, and F1 scores?

Decision metrics answer:

- Did the agent choose the expected gate action?
- Did it route human review correctly?
- Did it recall high-risk changes that should not silently pass?

## Run

```bash
python3 -m src.main --eval
```

Generated files:

- `outputs/classifier_eval_report.md`
- `outputs/decision_eval_report.md`
- `outputs/decision_eval_result.json`
- `outputs/judge_result.json`

## Metrics

The decision eval report includes:

- `decision_accuracy`: final gate action correctness.
- `review_routing_accuracy`: whether human review routing matched expectations.
- `high_risk_recall`: recall for samples labeled high-risk.
- failure details for mismatched actions or review routing.

## Interpreting Failures

Decision eval failures are not automatically test failures. They are tuning signals.

For example, an early quality gate may intentionally prioritize high-risk recall and route ambiguous cases to human review. That can reduce false negatives while increasing false positives. The failure table makes this tradeoff visible so rule weights, confidence thresholds, and domain knowledge can be tuned deliberately.

## Why This Matters

Enterprise agent systems should not be evaluated only by whether their text sounds useful. They need behavioral evals for decisions that affect release safety.

This eval layer makes the agent safer to change because every new rule, prompt, model, or workflow adjustment can be checked against expected business decisions.

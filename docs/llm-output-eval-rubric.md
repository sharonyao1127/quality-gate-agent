# LLM Output Eval Rubric

This rubric evaluates AI-generated PR reviews and risk comments.

## 1) Completeness
- Does the output cover all critical risk areas implied by the change summary?
- Are high-impact dimensions (data consistency, idempotency, external callback) included when relevant?

## 2) Correctness
- Are the identified risks technically correct for the described change?
- Are risk levels (high/medium/low) aligned with rule evidence?

## 3) Actionability
- Are recommendations concrete, testable, and execution-ready?
- Can QA or developers run the suggested checks without ambiguity?

## 4) Traceability
- Is each risk claim traceable to explicit change evidence (keywords, impacted area, contract changes)?
- Does the review explain *why* each risk was raised?

## 5) Safety
- Does the output avoid missing high-risk scenarios that could cause user or financial impact?
- Are critical cases (duplicate request, delayed callback, reconciliation) considered when applicable?

## 6) False Positive Control
- Does the output avoid over-alerting on low-risk copy/help-text-only changes?
- Are negative indicators used to downgrade or skip non-behavioral changes?

## Suggested Scoring
- 0 = missing / incorrect
- 1 = partially addressed
- 2 = fully addressed

Total score range: 0-12. Teams may set release thresholds (e.g., block merge if score < 8 for high-risk PRs).

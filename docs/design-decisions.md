# Design Decisions

## Why rule-based scoring first?

The first version uses structured rules and explainable scoring instead of relying directly on an LLM.

Reasons:

- QA risk decisions should be traceable.
- Risk scoring should be reviewable by humans.
- CI quality gates need stable and predictable behavior.
- LLM-generated suggestions can be added later as an assistant layer, not as the only decision maker.

## Why PR comment output?

QA feedback is most useful when it appears close to the engineering workflow.

A PR-ready comment helps connect quality analysis with code review, CI checks, and regression planning.

## Why eval cases?

A quality gate should not only generate results. It should also be evaluated.

Eval cases help detect false positives and false negatives, such as low-risk copy changes being incorrectly classified as high-risk.

# Risk Model

## Risk Dimensions

Each rule can define five risk dimensions:

| Dimension | Meaning |
|---|---|
| business_impact | How much the change may affect key business flows |
| data_consistency | Whether the change may affect financial/data consistency |
| user_visibility | Whether users can directly observe the issue |
| reversibility | Whether the issue is easy to rollback or compensate |
| external_dependency | Whether external systems/providers are involved |

Each dimension is scored from 0 to 3.

## Risk Score

```text
risk_score = sum(dimensions)
```

Maximum score is 15.

## Risk Level

```text
0-4   -> low
5-9   -> medium
10-15 -> high
```

## Overall Gate Risk

The overall gate risk uses the highest matched rule score.

Reason: one high-risk area should be enough to trigger careful regression review.

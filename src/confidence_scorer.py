from dataclasses import dataclass, field
from typing import List


@dataclass
class ConfidenceAssessment:
    score: int
    level: str
    review_required: bool
    reasons: List[str] = field(default_factory=list)


def assess_confidence(matches, total_rules_evaluated: int) -> ConfidenceAssessment:
    """Estimate confidence using explainable rule-evidence heuristics."""
    reasons: List[str] = []

    if total_rules_evaluated <= 0:
        return ConfidenceAssessment(
            score=40,
            level="low",
            review_required=True,
            reasons=["No rules were evaluated."],
        )

    score = 60
    score += min(25, len(matches) * 10)

    if matches:
        keyword_counts = [len(match.matched_keywords) for match in matches]
        if all(count >= 2 for count in keyword_counts):
            score += 10
            reasons.append("All matched rules have at least two keyword signals.")
        if any(count == 1 for count in keyword_counts):
            score -= 15
            reasons.append("At least one rule matched on a single keyword.")
        reasons.append(f"{len(matches)} of {total_rules_evaluated} evaluated rules matched.")
    else:
        score -= 10
        reasons.append("No rules matched the change text.")

    score = max(0, min(100, score))

    if score >= 80:
        level = "high"
    elif score >= 60:
        level = "medium"
    else:
        level = "low"

    return ConfidenceAssessment(
        score=score,
        level=level,
        review_required=score < 70,
        reasons=reasons,
    )

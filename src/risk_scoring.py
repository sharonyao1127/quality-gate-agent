from typing import Dict, Iterable

RISK_LEVEL_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

RISK_THRESHOLDS = {
    "high": 10,
    "medium": 5,
}


def score_dimensions(dimensions: Dict[str, int]) -> int:
    """Calculate a score from risk dimensions.

    Each dimension is expected to be 0-3.
    """
    return sum(int(value) for value in dimensions.values())


def calculate_level_from_score(score: int) -> str:
    if score >= RISK_THRESHOLDS["high"]:
        return "high"
    if score >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def merge_risk_scores(scores: Iterable[int]) -> int:
    """Use max score for overall gate risk.

    In quality gates, one high-risk area should be enough to trigger high attention.
    """
    scores = list(scores)
    return max(scores) if scores else 0


def downgrade_risk_once(score: int) -> int:
    """Downgrade risk score by one level while keeping threshold semantics.

    high (>=10) -> medium cap (9)
    medium (5-9) -> low cap (4)
    low (0-4) -> unchanged
    """
    level = calculate_level_from_score(score)
    if level == "high":
        return min(score, RISK_THRESHOLDS["high"] - 1)
    if level == "medium":
        return min(score, RISK_THRESHOLDS["medium"] - 1)
    return score

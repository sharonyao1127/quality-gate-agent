from dataclasses import dataclass, field
from typing import List

from src.gate_analyzer import GateAnalysisResult


@dataclass
class GateDecision:
    action: str
    review_required: bool
    merge_blocked: bool
    reasons: List[str] = field(default_factory=list)
    required_followups: List[str] = field(default_factory=list)


def decide_gate(result: GateAnalysisResult, strict: bool = False) -> GateDecision:
    reasons: List[str] = []
    required_followups: List[str] = []

    if result.overall_risk_level == "high":
        reasons.append("Overall risk is high.")
        required_followups.append("Review high-risk findings before merge or release.")

    if result.confidence and result.confidence.review_required:
        reasons.append(
            f"Confidence is {result.confidence.level} ({result.confidence.score}/100), requiring human review."
        )
        required_followups.append("Confirm whether the low-confidence finding is a false positive or missed risk.")

    if result.llm_result is not None:
        reasons.append("LLM classification was used and should be treated as advisory evidence.")

    if strict and result.overall_risk_level == "high":
        return GateDecision(
            action="fail",
            review_required=True,
            merge_blocked=True,
            reasons=reasons,
            required_followups=required_followups,
        )

    if result.overall_risk_level == "high" or (result.confidence and result.confidence.review_required):
        return GateDecision(
            action="human_review_required",
            review_required=True,
            merge_blocked=False,
            reasons=reasons,
            required_followups=required_followups,
        )

    if result.overall_risk_level == "medium":
        return GateDecision(
            action="targeted_regression",
            review_required=False,
            merge_blocked=False,
            reasons=["Overall risk is medium."],
            required_followups=["Run targeted regression checks before release."],
        )

    return GateDecision(
        action="pass",
        review_required=False,
        merge_blocked=False,
        reasons=["No blocking risk detected by the current gate."],
        required_followups=[],
    )

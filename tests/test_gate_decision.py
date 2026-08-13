from src.confidence_scorer import ConfidenceAssessment
from src.gate_analyzer import GateAnalysisResult
from src.gate_decision import decide_gate


def test_decide_gate_passes_low_risk_high_confidence_result():
    result = GateAnalysisResult(
        matches=[],
        overall_risk_level="low",
        overall_risk_score=0,
        confidence=ConfidenceAssessment(score=85, level="high", review_required=False),
    )

    decision = decide_gate(result)

    assert decision.action == "pass"
    assert decision.review_required is False
    assert decision.merge_blocked is False


def test_decide_gate_recommends_targeted_regression_for_medium_risk():
    result = GateAnalysisResult(
        matches=[],
        overall_risk_level="medium",
        overall_risk_score=7,
        confidence=ConfidenceAssessment(score=80, level="high", review_required=False),
    )

    decision = decide_gate(result)

    assert decision.action == "targeted_regression"
    assert decision.review_required is False
    assert "Run targeted regression checks before release." in decision.required_followups


def test_decide_gate_requires_human_review_for_high_risk():
    result = GateAnalysisResult(
        matches=[],
        overall_risk_level="high",
        overall_risk_score=12,
        confidence=ConfidenceAssessment(score=90, level="high", review_required=False),
    )

    decision = decide_gate(result)

    assert decision.action == "human_review_required"
    assert decision.review_required is True
    assert decision.merge_blocked is False


def test_decide_gate_blocks_merge_for_high_risk_in_strict_mode():
    result = GateAnalysisResult(
        matches=[],
        overall_risk_level="high",
        overall_risk_score=12,
        confidence=ConfidenceAssessment(score=90, level="high", review_required=False),
    )

    decision = decide_gate(result, strict=True)

    assert decision.action == "fail"
    assert decision.review_required is True
    assert decision.merge_blocked is True


def test_decide_gate_requires_review_for_low_confidence_result():
    result = GateAnalysisResult(
        matches=[],
        overall_risk_level="low",
        overall_risk_score=0,
        confidence=ConfidenceAssessment(score=55, level="low", review_required=True),
    )

    decision = decide_gate(result)

    assert decision.action == "human_review_required"
    assert decision.review_required is True
    assert decision.merge_blocked is False
    assert "low (55/100)" in decision.reasons[0]

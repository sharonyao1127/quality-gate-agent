from src.confidence_scorer import assess_confidence
from src.gate_analyzer import GateMatch, analyze_change
from src.pr_comment_generator import generate_pr_comment
from src.report_generator import generate_gate_report


def test_assess_confidence_requires_review_when_no_rules_evaluated():
    confidence = assess_confidence(matches=[], total_rules_evaluated=0)

    assert confidence.level == "low"
    assert confidence.score == 40
    assert confidence.review_required is True
    assert "No rules were evaluated." in confidence.reasons


def test_assess_confidence_is_high_when_matches_have_multiple_keywords():
    matches = [
        GateMatch(
            id="async_callback_risk",
            name="Async Callback Risk",
            risk_level="high",
            risk_score=13,
            matched_keywords=["timeout", "callback", "provider"],
            impacted_areas=["external provider callback"],
            suggested_regression=["Simulate provider timeout."],
            dimensions={"business_impact": 3},
        )
    ]

    confidence = assess_confidence(matches=matches, total_rules_evaluated=3)

    assert confidence.level == "high"
    assert confidence.review_required is False


def test_analyze_change_attaches_confidence_assessment():
    result = analyze_change(
        "Provider callback timeout needs status update.",
        [
            {
                "id": "async_callback_risk",
                "name": "Async Callback Risk",
                "keywords": ["provider", "callback", "timeout"],
                "dimensions": {
                    "business_impact": 3,
                    "data_consistency": 3,
                    "user_visibility": 2,
                    "reversibility": 2,
                    "external_dependency": 3,
                },
            }
        ],
    )

    assert result.confidence is not None
    assert result.confidence.level == "high"
    assert result.confidence.review_required is False


def test_reports_include_confidence_assessment():
    result = analyze_change(
        "Only mentions callback once.",
        [
            {
                "id": "async_callback_risk",
                "name": "Async Callback Risk",
                "keywords": ["callback"],
                "dimensions": {
                    "business_impact": 1,
                    "data_consistency": 1,
                    "user_visibility": 1,
                    "reversibility": 1,
                    "external_dependency": 1,
                },
            }
        ],
    )

    report = generate_gate_report(result)
    pr_comment = generate_pr_comment(result)

    assert "## Confidence Assessment" in report
    assert "Human Review Required" in report
    assert "### Confidence" in pr_comment
    assert "Human review required: yes" in pr_comment

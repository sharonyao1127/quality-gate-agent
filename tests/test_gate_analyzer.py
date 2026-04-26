from src.gate_analyzer import analyze_change


def test_analyze_change_matches_async_callback_risk():
    change_text = "The provider request may timeout and delayed callback will update status."
    rules = [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["timeout", "callback", "delayed", "provider"],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
            "impacted_areas": ["external provider callback"],
            "suggested_regression": ["Simulate provider timeout."],
        }
    ]

    result = analyze_change(change_text, rules)

    assert len(result.matches) == 1
    assert result.matches[0].id == "async_callback_risk"
    assert result.overall_risk_level == "high"
    assert result.overall_risk_score == 13


def test_analyze_change_returns_low_when_no_match():
    result = analyze_change("Only update copywriting text.", [])
    assert result.overall_risk_level == "low"
    assert result.overall_risk_score == 0

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


def test_analyze_change_downgrades_high_risk_when_negative_keywords_matched():
    change_text = "Update provider callback help text only, copywriting-only, no business behavior changed."
    rules = [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["callback", "provider"],
            "negative_keywords": ["copywriting-only", "help text", "no business behavior changed"],
            "negative_match_action": "downgrade",
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
        }
    ]

    result = analyze_change(change_text, rules)

    assert len(result.matches) == 1
    assert result.matches[0].risk_level == "medium"
    assert result.matches[0].risk_score == 9
    assert result.overall_risk_level == "medium"
    assert result.overall_risk_score == 9


def test_analyze_change_skips_rule_when_negative_keywords_match_and_action_is_skip():
    change_text = "Provider callback help text updated, copywriting-only, no business behavior changed."
    rules = [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["callback", "provider"],
            "negative_keywords": ["copywriting-only", "help text", "no business behavior changed"],
            "negative_match_action": "skip",
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
        }
    ]

    result = analyze_change(change_text, rules)

    assert len(result.matches) == 0
    assert result.overall_risk_level == "low"
    assert result.overall_risk_score == 0


def test_analyze_change_defaults_to_downgrade_when_negative_action_invalid():
    change_text = "Provider callback help text updated, no business behavior changed."
    rules = [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["callback", "provider"],
            "negative_keywords": ["help text", "no business behavior changed"],
            "negative_match_action": "ignore",
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
        }
    ]

    result = analyze_change(change_text, rules)

    assert len(result.matches) == 1
    assert result.matches[0].risk_level == "medium"
    assert result.matches[0].risk_score == 9


def test_analyze_change_does_not_downgrade_on_weak_negative_evidence():
    change_text = "The provider callback may timeout. Only help text was mentioned once."
    rules = [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["callback", "provider", "timeout"],
            "negative_keywords": ["copywriting-only", "help text", "no business behavior changed"],
            "negative_match_action": "downgrade",
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
        }
    ]

    result = analyze_change(change_text, rules)

    assert len(result.matches) == 1
    assert result.matches[0].risk_level == "high"
    assert result.matches[0].risk_score == 13

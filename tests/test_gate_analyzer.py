from src.gate_analyzer import analyze_change, find_keyword_locations


def test_find_keyword_locations_returns_1_based_line_numbers():
    change_text = """Update payment retry handling.
Provider callback can be delayed.
No balance deduction change."""

    locations = find_keyword_locations(change_text, ["retry", "callback", "balance"])

    assert locations == {
        "retry": [1],
        "callback": [2],
        "balance": [3],
    }


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


def test_analyze_change_traces_keyword_locations():
    change_text = """The provider request may timeout.
Delayed callback will update transaction status."""
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
        }
    ]

    result = analyze_change(change_text, rules)

    match_trace = result.trace.match_traces[0]
    assert match_trace.line_numbers == [1, 2]
    assert match_trace.keyword_locations["timeout"] == [1]
    assert match_trace.keyword_locations["callback"] == [2]


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

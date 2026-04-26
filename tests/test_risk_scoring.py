from src.risk_scoring import calculate_level_from_score, merge_risk_scores, score_dimensions


def test_score_dimensions():
    dimensions = {
        "business_impact": 3,
        "data_consistency": 3,
        "user_visibility": 2,
        "reversibility": 2,
        "external_dependency": 3,
    }

    assert score_dimensions(dimensions) == 13


def test_calculate_level_from_score():
    assert calculate_level_from_score(0) == "low"
    assert calculate_level_from_score(5) == "medium"
    assert calculate_level_from_score(10) == "high"


def test_merge_risk_scores_uses_max_score():
    assert merge_risk_scores([3, 8, 13]) == 13
    assert merge_risk_scores([]) == 0

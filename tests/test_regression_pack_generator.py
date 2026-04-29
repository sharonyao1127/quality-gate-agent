from src.gate_analyzer import analyze_change
from src.regression_pack_generator import generate_regression_pack


def test_generate_regression_pack_builds_structured_required_checks():
    rules = [
        {
            "id": "combo_risk",
            "name": "Combined Risk",
            "keywords": ["retry", "callback", "status"],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
            "impacted_areas": [
                "idempotency",
                "external provider callback",
                "frontend/backend consistency",
            ],
        }
    ]
    result = analyze_change("retry callback status", rules)

    pack = generate_regression_pack(result)

    assert pack["risk_level"] == "high"
    check_ids = [check["id"] for check in pack["required_checks"]]
    assert "duplicate_request_check" in check_ids
    assert "delayed_callback_check" in check_ids
    assert "status_display_check" in check_ids


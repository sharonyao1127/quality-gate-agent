from src.gate_analyzer import analyze_change


def _stable_result_snapshot(result):
    return {
        "overall_risk_level": result.overall_risk_level,
        "overall_risk_score": result.overall_risk_score,
        "matches": [
            {
                "id": match.id,
                "risk_level": match.risk_level,
                "risk_score": match.risk_score,
                "matched_keywords": match.matched_keywords,
                "impacted_areas": match.impacted_areas,
                "suggested_regression": match.suggested_regression,
                "dimensions": match.dimensions,
            }
            for match in result.matches
        ],
        "trace": {
            "input_hash": result.trace.input_hash if result.trace else None,
            "input_type": result.trace.input_type if result.trace else None,
            "rules_matched": result.trace.rules_matched if result.trace else [],
            "total_rules_evaluated": result.trace.total_rules_evaluated if result.trace else 0,
        },
        "confidence": {
            "score": result.confidence.score if result.confidence else None,
            "level": result.confidence.level if result.confidence else None,
            "review_required": result.confidence.review_required if result.confidence else None,
            "reasons": result.confidence.reasons if result.confidence else [],
        },
    }


def test_analyze_change_is_idempotent_for_stable_business_output():
    change_text = (
        "The payment retry flow now stores provider_request_id, handles delayed callback, "
        "and updates transaction status after provider confirmation."
    )
    rules = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "keywords": ["retry", "provider_request_id", "transaction"],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 1,
            },
            "impacted_areas": ["idempotency", "transaction record uniqueness"],
            "suggested_regression": ["Submit duplicated request with same request ID."],
        },
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["delayed", "callback", "provider"],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
            "impacted_areas": ["external provider callback", "transaction final state"],
            "suggested_regression": ["Simulate delayed success callback."],
        },
    ]

    first = analyze_change(change_text, rules, input_type="api_change")
    second = analyze_change(change_text, rules, input_type="api_change")

    assert _stable_result_snapshot(first) == _stable_result_snapshot(second)

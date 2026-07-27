from src.gate_analyzer import analyze_change, GateMatch
from src.llm_risk_classifier import LLMClassificationResult, LLMRiskFinding, LLMRiskClassifier


def _make_mock_classifier():
    classifier = LLMRiskClassifier(api_key="test-key")
    classifier._call_chat_completion = lambda prompt: LLMClassificationResult(
        findings=[
            LLMRiskFinding(
                rule_id="async_callback_risk",
                rule_name="Async Callback Risk",
                risk_level="high",
                risk_score=13,
                reasoning="Timeout and callback handling present.",
                impacted_areas=["external provider callback"],
                suggested_regression=["Simulate timeout."],
                dimensions={
                    "business_impact": 3,
                    "data_consistency": 3,
                    "user_visibility": 2,
                    "reversibility": 2,
                    "external_dependency": 3,
                },
                confidence="high",
            )
        ],
        overall_risk_level="high",
        overall_risk_score=13,
        summary="Mock LLM result.",
    ).model_dump_json()
    return classifier


def test_llm_mode_replaces_keyword_matches():
    rules = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "keywords": ["retry"],
            "dimensions": {"business_impact": 3},
            "impacted_areas": ["idempotency"],
            "suggested_regression": ["Test duplicate."],
        }
    ]
    classifier = _make_mock_classifier()
    result = analyze_change(
        "timeout callback provider",
        rules,
        classifier_mode="llm",
        llm_classifier=classifier,
    )

    assert len(result.matches) == 1
    assert result.matches[0].id == "async_callback_risk"
    assert result.matches[0].source == "llm"
    assert result.matches[0].reasoning == "Timeout and callback handling present."
    assert result.llm_result is not None


def test_hybrid_mode_merges_keyword_and_llm():
    rules = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "keywords": ["retry"],
            "dimensions": {"business_impact": 3, "data_consistency": 3, "user_visibility": 2, "reversibility": 2, "external_dependency": 1},
            "impacted_areas": ["idempotency"],
            "suggested_regression": ["Test duplicate."],
        }
    ]
    classifier = _make_mock_classifier()
    result = analyze_change(
        "retry request_id timeout callback",
        rules,
        classifier_mode="hybrid",
        llm_classifier=classifier,
    )

    ids = {match.id for match in result.matches}
    assert ids == {"idempotency_risk", "async_callback_risk"}
    assert result.llm_result is not None


def test_keyword_mode_ignores_classifier():
    rules = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "keywords": ["retry"],
            "dimensions": {"business_impact": 3},
            "impacted_areas": ["idempotency"],
            "suggested_regression": ["Test duplicate."],
        }
    ]
    classifier = _make_mock_classifier()
    result = analyze_change(
        "retry request_id",
        rules,
        classifier_mode="keyword",
        llm_classifier=classifier,
    )

    assert len(result.matches) == 1
    assert result.matches[0].id == "idempotency_risk"
    assert result.matches[0].source == "keyword"
    assert result.llm_result is None

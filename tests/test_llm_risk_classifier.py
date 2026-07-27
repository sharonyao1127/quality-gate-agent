from unittest.mock import patch, MagicMock

from src.llm_risk_classifier import (
    LLMRiskClassifier,
    LLMClassificationResult,
    LLMRiskFinding,
    merge_llm_into_keyword_result,
)


def test_classifier_not_available_without_api_key():
    classifier = LLMRiskClassifier(api_key=None)
    assert classifier.is_available() is False
    assert classifier.classify("change", []) is None


def test_classifier_parses_valid_llm_response():
    classifier = LLMRiskClassifier(api_key="test-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": LLMClassificationResult(
                        findings=[
                            LLMRiskFinding(
                                rule_id="idempotency_risk",
                                rule_name="Idempotency Risk",
                                risk_level="high",
                                risk_score=11,
                                reasoning="Retry logic may double deduct balance.",
                                impacted_areas=["idempotency", "balance consistency"],
                                suggested_regression=["Submit duplicated request."],
                                dimensions={
                                    "business_impact": 3,
                                    "data_consistency": 3,
                                    "user_visibility": 2,
                                    "reversibility": 2,
                                    "external_dependency": 1,
                                },
                                confidence="high",
                            )
                        ],
                        overall_risk_level="high",
                        overall_risk_score=11,
                        summary="High risk detected.",
                    ).model_dump_json()
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response):
        result = classifier.classify("change", [])

    assert result is not None
    assert result.overall_risk_level == "high"
    assert result.overall_risk_score == 11
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "idempotency_risk"


def test_classifier_returns_none_on_invalid_json():
    classifier = LLMRiskClassifier(api_key="test-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "not valid json"}}],
        "usage": {},
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response):
        result = classifier.classify("change", [])

    assert result is None


def test_merge_llm_into_keyword_result_adds_new_finding():
    keyword = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "risk_level": "high",
            "risk_score": 11,
            "matched_keywords": ["retry"],
            "impacted_areas": ["idempotency"],
            "suggested_regression": ["Test duplicate."],
            "dimensions": {"business_impact": 3, "data_consistency": 3, "user_visibility": 2, "reversibility": 2, "external_dependency": 1},
            "source": "keyword",
            "reasoning": "",
        }
    ]
    llm_result = LLMClassificationResult(
        findings=[
            LLMRiskFinding(
                rule_id="async_callback_risk",
                rule_name="Async Callback Risk",
                risk_level="high",
                risk_score=13,
                reasoning="Timeout and callback handling.",
                impacted_areas=["external provider callback"],
                suggested_regression=["Simulate timeout."],
                dimensions={"business_impact": 3, "data_consistency": 3, "user_visibility": 2, "reversibility": 2, "external_dependency": 3},
                confidence="high",
            )
        ],
        overall_risk_level="high",
        overall_risk_score=13,
        summary="Merged result.",
    )

    merged = merge_llm_into_keyword_result(keyword, llm_result)

    assert len(merged) == 2
    ids = {m["id"] for m in merged}
    assert ids == {"idempotency_risk", "async_callback_risk"}

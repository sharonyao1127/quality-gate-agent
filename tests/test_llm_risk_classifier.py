import json
from unittest.mock import patch, MagicMock

import pytest

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


def test_classifier_returns_none_when_llm_level_and_score_conflict():
    classifier = LLMRiskClassifier(api_key="test-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": {
                        "findings": [
                            {
                                "rule_id": "idempotency_risk",
                                "rule_name": "Idempotency Risk",
                                "risk_level": "high",
                                "risk_score": 9,
                                "reasoning": "The score and level conflict.",
                                "impacted_areas": ["idempotency"],
                                "suggested_regression": ["Test duplicate."],
                                "dimensions": {
                                    "business_impact": 3,
                                    "data_consistency": 2,
                                    "user_visibility": 1,
                                    "reversibility": 1,
                                    "external_dependency": 2,
                                },
                                "confidence": "high",
                            }
                        ],
                        "overall_risk_level": "high",
                        "overall_risk_score": 9,
                        "summary": "Invalid score/level pair.",
                    }
                }
            }
        ],
        "usage": {},
    }
    mock_response.json.return_value["choices"][0]["message"]["content"] = json.dumps(
        mock_response.json.return_value["choices"][0]["message"]["content"]
    )
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response):
        result = classifier.classify("change", [])

    assert result is None


def test_llm_classification_rejects_overall_score_that_does_not_match_findings():
    with pytest.raises(ValueError):
        LLMClassificationResult(
            findings=[
                LLMRiskFinding(
                    rule_id="idempotency_risk",
                    rule_name="Idempotency Risk",
                    risk_level="medium",
                    risk_score=7,
                    reasoning="Medium risk.",
                    impacted_areas=["idempotency"],
                    suggested_regression=["Test duplicate."],
                    dimensions={"business_impact": 3, "data_consistency": 2, "user_visibility": 1, "reversibility": 1},
                    confidence="medium",
                )
            ],
            overall_risk_level="high",
            overall_risk_score=10,
            summary="Overall score should match max finding score.",
        )


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


def test_merge_llm_into_keyword_result_does_not_mutate_keyword_matches():
    keyword = [
        {
            "id": "idempotency_risk",
            "name": "Idempotency Risk",
            "risk_level": "high",
            "risk_score": 11,
            "matched_keywords": ["retry"],
            "impacted_areas": ["idempotency"],
            "suggested_regression": ["Test duplicate."],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 1,
            },
            "source": "keyword",
            "reasoning": "",
        }
    ]
    llm_result = LLMClassificationResult(
        findings=[
            LLMRiskFinding(
                rule_id="idempotency_risk",
                rule_name="Idempotency Risk",
                risk_level="high",
                risk_score=13,
                reasoning="LLM adds extra regression evidence.",
                impacted_areas=["balance consistency"],
                suggested_regression=["Verify only one transaction record is created."],
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
        summary="Merged result.",
    )

    merged = merge_llm_into_keyword_result(keyword, llm_result)

    assert merged[0]["impacted_areas"] == ["idempotency", "balance consistency"]
    assert merged[0]["suggested_regression"] == [
        "Test duplicate.",
        "Verify only one transaction record is created.",
    ]
    assert keyword[0]["impacted_areas"] == ["idempotency"]
    assert keyword[0]["suggested_regression"] == ["Test duplicate."]

import pytest

from src.gate_analyzer import GateAnalysisResult, GateMatch
from src.schema_validator import ValidationError, validate_gate_analysis_result
from src.traceability import AnalysisTrace


def test_validate_gate_analysis_result_passes_with_valid_payload():
    result = GateAnalysisResult(
        matches=[
            GateMatch(
                id="rule_1",
                name="Rule One",
                risk_level="medium",
                risk_score=7,
                matched_keywords=["retry"],
                impacted_areas=["payment"],
                suggested_regression=["idempotency test"],
                dimensions={"business_impact": 3, "data_consistency": 2},
            )
        ],
        overall_risk_level="medium",
        overall_risk_score=7,
        trace=AnalysisTrace(
            input_hash="abc123def456",
            input_type="generic",
            ruleset_version="1.0",
            total_rules_evaluated=5,
            rules_matched=["rule_1"],
            execution_time_ms=10.5,
            timestamp="2026-01-01T00:00:00",
        ),
    )

    validate_gate_analysis_result(result)


def test_validate_gate_analysis_result_raises_on_invalid_match_shape():
    result = GateAnalysisResult(
        matches=[
            GateMatch(
                id="rule_1",
                name="Rule One",
                risk_level="medium",
                risk_score=7,
                matched_keywords=["retry"],
                impacted_areas=["payment"],
                suggested_regression=["idempotency test"],
                dimensions={"business_impact": "bad_type"},  # type: ignore[dict-item]
            )
        ],
        overall_risk_level="medium",
        overall_risk_score=7,
        trace=None,
    )

    with pytest.raises(ValidationError):
        validate_gate_analysis_result(result)

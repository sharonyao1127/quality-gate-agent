from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from src.gate_analyzer import GateAnalysisResult
from src.risk_scoring import calculate_level_from_score


VALID_RISK_LEVELS = {"low", "medium", "high"}
VALID_DIMENSION_KEYS = {
    "business_impact",
    "data_consistency",
    "user_visibility",
    "reversibility",
    "external_dependency",
}


class GateMatchSchema(BaseModel):
    id: str
    name: str
    risk_level: str
    risk_score: int
    matched_keywords: List[str]
    impacted_areas: List[str]
    suggested_regression: List[str]
    dimensions: Dict[str, int]

    @model_validator(mode="after")
    def validate_semantics(self) -> "GateMatchSchema":
        if self.risk_level not in VALID_RISK_LEVELS:
            raise ValueError(f"Invalid risk_level '{self.risk_level}'")
        if self.risk_score < 0 or self.risk_score > 15:
            raise ValueError(f"risk_score out of range: {self.risk_score}")

        expected_level = calculate_level_from_score(self.risk_score)
        if self.risk_level != expected_level:
            raise ValueError(
                f"risk_level '{self.risk_level}' does not match risk_score {self.risk_score} (expected '{expected_level}')"
            )

        invalid_keys = [key for key in self.dimensions if key not in VALID_DIMENSION_KEYS]
        if invalid_keys:
            raise ValueError(f"Unknown dimension keys: {invalid_keys}")

        for key, value in self.dimensions.items():
            if value < 0 or value > 3:
                raise ValueError(f"Dimension '{key}' out of range: {value}")
        return self


class AnalysisTraceSchema(BaseModel):
    input_hash: str
    input_type: str
    ruleset_version: str
    total_rules_evaluated: int
    rules_matched: List[str]
    execution_time_ms: float
    timestamp: str


class GateAnalysisResultSchema(BaseModel):
    matches: List[GateMatchSchema]
    overall_risk_level: str
    overall_risk_score: int
    trace: Optional[AnalysisTraceSchema] = Field(default=None)

    @model_validator(mode="after")
    def validate_semantics(self) -> "GateAnalysisResultSchema":
        if self.overall_risk_level not in VALID_RISK_LEVELS:
            raise ValueError(f"Invalid overall_risk_level '{self.overall_risk_level}'")
        if self.overall_risk_score < 0 or self.overall_risk_score > 15:
            raise ValueError(f"overall_risk_score out of range: {self.overall_risk_score}")

        expected_level = calculate_level_from_score(self.overall_risk_score)
        if self.overall_risk_level != expected_level:
            raise ValueError(
                "overall_risk_level does not match overall_risk_score: "
                f"{self.overall_risk_level} vs expected {expected_level}"
            )
        return self


def validate_gate_analysis_result(result: GateAnalysisResult) -> None:
    payload = {
        "matches": [
            {
                "id": match.id,
                "name": match.name,
                "risk_level": match.risk_level,
                "risk_score": match.risk_score,
                "matched_keywords": match.matched_keywords,
                "impacted_areas": match.impacted_areas,
                "suggested_regression": match.suggested_regression,
                "dimensions": match.dimensions,
            }
            for match in result.matches
        ],
        "overall_risk_level": result.overall_risk_level,
        "overall_risk_score": result.overall_risk_score,
        "trace": (
            {
                "input_hash": result.trace.input_hash,
                "input_type": result.trace.input_type,
                "ruleset_version": result.trace.ruleset_version,
                "total_rules_evaluated": result.trace.total_rules_evaluated,
                "rules_matched": result.trace.rules_matched,
                "execution_time_ms": result.trace.execution_time_ms,
                "timestamp": result.trace.timestamp,
            }
            if result.trace
            else None
        ),
    }
    GateAnalysisResultSchema.model_validate(payload)


__all__ = [
    "GateAnalysisResultSchema",
    "ValidationError",
    "validate_gate_analysis_result",
]

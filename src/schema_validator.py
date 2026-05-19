from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from src.gate_analyzer import GateAnalysisResult


class GateMatchSchema(BaseModel):
    id: str
    name: str
    risk_level: str
    risk_score: int
    matched_keywords: List[str]
    impacted_areas: List[str]
    suggested_regression: List[str]
    dimensions: Dict[str, int]


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

from dataclasses import dataclass
from typing import Any, Dict, List
import yaml

from src.risk_scoring import (
    calculate_level_from_score,
    downgrade_risk_once,
    merge_risk_scores,
    score_dimensions,
)


@dataclass
class GateMatch:
    id: str
    name: str
    risk_level: str
    risk_score: int
    matched_keywords: List[str]
    impacted_areas: List[str]
    suggested_regression: List[str]
    dimensions: Dict[str, int]


@dataclass
class GateAnalysisResult:
    matches: List[GateMatch]
    overall_risk_level: str
    overall_risk_score: int


def load_gate_rules(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])


def analyze_change(change_text: str, rules: List[Dict[str, Any]]) -> GateAnalysisResult:
    """Analyze change text based on structured quality gate rules."""
    text_lower = change_text.lower()
    matches: List[GateMatch] = []

    for rule in rules:
        keywords = rule.get("keywords", [])
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        negative_keywords = rule.get("negative_keywords", [])
        matched_negative = [kw for kw in negative_keywords if kw.lower() in text_lower]

        if matched:
            negative_match_action = rule.get("negative_match_action", "downgrade")

            if matched_negative and negative_match_action == "skip":
                continue

            dimensions = rule.get("dimensions", {})
            risk_score = score_dimensions(dimensions)
            risk_level = calculate_level_from_score(risk_score)

            if matched_negative and negative_match_action == "downgrade":
                risk_score = downgrade_risk_once(risk_score)
                risk_level = calculate_level_from_score(risk_score)


            matches.append(
                GateMatch(
                    id=rule["id"],
                    name=rule["name"],
                    risk_level=risk_level,
                    risk_score=risk_score,
                    matched_keywords=matched,
                    impacted_areas=rule.get("impacted_areas", []),
                    suggested_regression=rule.get("suggested_regression", []),
                    dimensions=dimensions,
                )
            )

    overall_score = merge_risk_scores(match.risk_score for match in matches)
    overall_level = calculate_level_from_score(overall_score)

    return GateAnalysisResult(
        matches=matches,
        overall_risk_level=overall_level,
        overall_risk_score=overall_score,
    )

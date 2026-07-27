from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import yaml
import time

from src.risk_scoring import (
    calculate_level_from_score,
    downgrade_risk_once,
    merge_risk_scores,
    score_dimensions,
)
from src.confidence_scorer import ConfidenceAssessment, assess_confidence
from src.traceability import AnalysisTrace, TraceabilityLogger
from src.llm_risk_classifier import (
    LLMRiskClassifier,
    LLMClassificationResult,
    merge_llm_into_keyword_result,
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
    source: str = "keyword"
    reasoning: str = ""


@dataclass
class GateAnalysisResult:
    matches: List[GateMatch]
    overall_risk_level: str
    overall_risk_score: int
    trace: Optional[AnalysisTrace] = field(default=None)
    confidence: Optional[ConfidenceAssessment] = field(default=None)
    llm_result: Optional[LLMClassificationResult] = field(default=None)


def load_gate_rules(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])


def find_keyword_locations(change_text: str, keywords: List[str]) -> Dict[str, List[int]]:
    lines = change_text.splitlines()
    locations: Dict[str, List[int]] = {}

    for keyword in keywords:
        keyword_lower = keyword.lower()
        line_numbers = [
            line_number
            for line_number, line in enumerate(lines, start=1)
            if keyword_lower in line.lower()
        ]
        if line_numbers:
            locations[keyword] = line_numbers

    return locations


def analyze_change(
    change_text: str,
    rules: List[Dict[str, Any]],
    input_type: str = "generic",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    classifier_mode: str = "keyword",
) -> GateAnalysisResult:
    """Analyze change text based on structured quality gate rules.

    Args:
        change_text: The text to analyze
        rules: List of quality gate rules
        input_type: Type of input (git_diff, api_change, openapi, etc.)
        llm_classifier: Optional LLM-based classifier for hybrid or llm mode
        classifier_mode: One of "keyword", "llm", or "hybrid"

    Returns:
        GateAnalysisResult with traceability information
    """
    start_time = time.perf_counter()

    trace_logger = TraceabilityLogger()
    trace_logger.start_analysis(change_text, input_type)

    text_lower = change_text.lower()
    matches: List[GateMatch] = []
    valid_negative_actions = {"downgrade", "skip"}

    for rule in rules:
        rule_id = rule.get("id", "unknown")
        rule_name = rule.get("name", "Unknown Rule")

        keywords = rule.get("keywords", [])
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        negative_keywords = rule.get("negative_keywords", [])
        matched_negative = [kw for kw in negative_keywords if kw.lower() in text_lower]
        keyword_locations = find_keyword_locations(change_text, matched + matched_negative)

        # Log rule evaluation
        trace_logger.log_rule_evaluation(
            rule_id=rule_id,
            rule_name=rule_name,
            matched=bool(matched),
            matched_keywords=matched,
            negative_keywords=matched_negative,
            keyword_locations=keyword_locations,
        )

        if matched:
            negative_match_action = rule.get("negative_match_action", "downgrade")
            if negative_match_action not in valid_negative_actions:
                negative_match_action = "downgrade"

            negative_match_min_hits = int(rule.get("negative_match_min_hits", len(negative_keywords)))
            strong_negative_evidence = (
                bool(negative_keywords)
                and negative_match_min_hits > 0
                and len(matched_negative) >= negative_match_min_hits
            )

            if strong_negative_evidence and negative_match_action == "skip":
                continue

            dimensions = rule.get("dimensions", {})
            raw_score = score_dimensions(dimensions)
            risk_score = raw_score
            risk_level = calculate_level_from_score(risk_score)
            adjustment_reason = None

            if strong_negative_evidence and negative_match_action == "downgrade":
                risk_score = downgrade_risk_once(risk_score)
                risk_level = calculate_level_from_score(risk_score)
                adjustment_reason = f"Downgraded due to negative keywords: {matched_negative}"

            # Log score calculation for this match
            trace_logger.log_score_calculation(
                dimensions=dimensions,
                raw_score=raw_score,
                final_score=risk_score,
                adjustment_reason=adjustment_reason,
            )

            matches.append(
                GateMatch(
                    id=rule_id,
                    name=rule_name,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    matched_keywords=matched,
                    impacted_areas=rule.get("impacted_areas", []),
                    suggested_regression=rule.get("suggested_regression", []),
                    dimensions=dimensions,
                )
            )

    llm_result: Optional[LLMClassificationResult] = None
    if classifier_mode in {"llm", "hybrid"} and llm_classifier is not None:
        llm_result = llm_classifier.classify(change_text, rules)
        if llm_result is not None:
            if classifier_mode == "llm":
                matches = [
                    GateMatch(
                        id=finding.rule_id,
                        name=finding.rule_name,
                        risk_level=finding.risk_level,
                        risk_score=finding.risk_score,
                        matched_keywords=["llm-classified"],
                        impacted_areas=finding.impacted_areas,
                        suggested_regression=finding.suggested_regression,
                        dimensions=finding.dimensions,
                        source="llm",
                        reasoning=finding.reasoning,
                    )
                    for finding in llm_result.findings
                ]
            else:  # hybrid
                keyword_dicts = [
                    {
                        "id": match.id,
                        "name": match.name,
                        "risk_level": match.risk_level,
                        "risk_score": match.risk_score,
                        "matched_keywords": match.matched_keywords,
                        "impacted_areas": match.impacted_areas,
                        "suggested_regression": match.suggested_regression,
                        "dimensions": match.dimensions,
                        "source": match.source,
                        "reasoning": match.reasoning,
                    }
                    for match in matches
                ]
                merged = merge_llm_into_keyword_result(keyword_dicts, llm_result)
                matches = []
                for item in merged:
                    matches.append(
                        GateMatch(
                            id=item["id"],
                            name=item["name"],
                            risk_level=item["risk_level"],
                            risk_score=item["risk_score"],
                            matched_keywords=item["matched_keywords"],
                            impacted_areas=item["impacted_areas"],
                            suggested_regression=item["suggested_regression"],
                            dimensions=item["dimensions"],
                            source=item.get("source", "keyword"),
                            reasoning=item.get("reasoning", ""),
                        )
                    )

    overall_score = merge_risk_scores(match.risk_score for match in matches)
    overall_level = calculate_level_from_score(overall_score)

    # Calculate execution time and finalize trace
    execution_time_ms = (time.perf_counter() - start_time) * 1000
    trace = trace_logger.finalize(execution_time_ms)
    confidence = assess_confidence(matches, total_rules_evaluated=len(rules))

    return GateAnalysisResult(
        matches=matches,
        overall_risk_level=overall_level,
        overall_risk_score=overall_score,
        trace=trace,
        confidence=confidence,
        llm_result=llm_result,
    )

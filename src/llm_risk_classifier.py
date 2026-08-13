"""LLM-based risk classifier with structured output and keyword fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, field_validator, model_validator

from src.risk_scoring import calculate_level_from_score, merge_risk_scores


VALID_DIMENSION_KEYS = {
    "business_impact",
    "data_consistency",
    "user_visibility",
    "reversibility",
    "external_dependency",
}


class LLMRiskFinding(BaseModel):
    rule_id: str
    rule_name: str
    risk_level: str
    risk_score: int
    reasoning: str
    impacted_areas: List[str]
    suggested_regression: List[str]
    dimensions: Dict[str, int]
    confidence: str

    @field_validator("risk_level", "confidence")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError(f"Invalid level: {value}")
        return value

    @field_validator("risk_score")
    @classmethod
    def _validate_score(cls, value: int) -> int:
        if value < 0 or value > 15:
            raise ValueError(f"risk_score out of range: {value}")
        return value

    @field_validator("dimensions")
    @classmethod
    def _validate_dimensions(cls, value: Dict[str, int]) -> Dict[str, int]:
        for key, score in value.items():
            if key not in VALID_DIMENSION_KEYS:
                raise ValueError(f"Unknown dimension key: {key}")
            if score < 0 or score > 3:
                raise ValueError(f"Dimension {key} score out of range: {score}")
        return value

    @model_validator(mode="after")
    def _validate_level_matches_score(self) -> "LLMRiskFinding":
        expected_level = calculate_level_from_score(self.risk_score)
        if self.risk_level != expected_level:
            raise ValueError(
                f"risk_level {self.risk_level} does not match risk_score {self.risk_score}; "
                f"expected {expected_level}"
            )
        return self


class LLMClassificationResult(BaseModel):
    findings: List[LLMRiskFinding]
    overall_risk_level: str
    overall_risk_score: int
    summary: str

    @field_validator("overall_risk_level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError(f"Invalid overall_risk_level: {value}")
        return value

    @field_validator("overall_risk_score")
    @classmethod
    def _validate_score(cls, value: int) -> int:
        if value < 0 or value > 15:
            raise ValueError(f"overall_risk_score out of range: {value}")
        return value

    @model_validator(mode="after")
    def _validate_level_matches_score(self) -> "LLMClassificationResult":
        expected_level = calculate_level_from_score(self.overall_risk_score)
        if self.overall_risk_level != expected_level:
            raise ValueError(
                f"overall_risk_level {self.overall_risk_level} does not match "
                f"overall_risk_score {self.overall_risk_score}; expected {expected_level}"
            )

        expected_score = merge_risk_scores(finding.risk_score for finding in self.findings)
        if self.overall_risk_score != expected_score:
            raise ValueError(
                f"overall_risk_score {self.overall_risk_score} does not match max finding score {expected_score}"
            )
        return self


@dataclass
class ClassifierUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""
    cached: bool = False


class LLMRiskClassifier:
    """Classify change text using an OpenAI-compatible chat completion API.

    Falls back gracefully when no API key is configured or the request fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self._model = model or os.getenv("QGA_MODEL", "gpt-4o-mini")
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self._api_key)

    def classify(
        self,
        change_text: str,
        rules: List[Dict[str, Any]],
    ) -> Optional[LLMClassificationResult]:
        """Return LLM-classified risks for the change text."""
        if not self._api_key:
            return None

        prompt = self._build_prompt(change_text, rules)
        try:
            response = self._call_chat_completion(prompt)
            return LLMClassificationResult.model_validate_json(response)
        except Exception:
            return None

    def classify_with_usage(
        self,
        change_text: str,
        rules: List[Dict[str, Any]],
    ) -> tuple[Optional[LLMClassificationResult], ClassifierUsage]:
        """Return classification plus token/latency usage metadata."""
        usage = ClassifierUsage(model=self._model)
        if not self._api_key:
            return None, usage

        prompt = self._build_prompt(change_text, rules)
        try:
            import time
            start = time.perf_counter()
            response_text, usage_dict = self._call_chat_completion_with_usage(prompt)
            usage.latency_ms = (time.perf_counter() - start) * 1000
            usage.prompt_tokens = usage_dict.get("prompt_tokens", 0)
            usage.completion_tokens = usage_dict.get("completion_tokens", 0)
            usage.total_tokens = usage_dict.get("total_tokens", 0)
            result = LLMClassificationResult.model_validate_json(response_text)
            return result, usage
        except Exception:
            return None, usage

    def _build_prompt(self, change_text: str, rules: List[Dict[str, Any]]) -> str:
        taxonomy = []
        for rule in rules:
            taxonomy.append(
                {
                    "id": rule.get("id", "unknown"),
                    "name": rule.get("name", "Unknown"),
                    "keywords": rule.get("keywords", []),
                    "impacted_areas": rule.get("impacted_areas", []),
                    "suggested_regression": rule.get("suggested_regression", []),
                }
            )

        schema = {
            "findings": [
                {
                    "rule_id": "string",
                    "rule_name": "string",
                    "risk_level": "low|medium|high",
                    "risk_score": "integer 0-15",
                    "reasoning": "string",
                    "impacted_areas": ["string"],
                    "suggested_regression": ["string"],
                    "dimensions": {
                        "business_impact": "0-3",
                        "data_consistency": "0-3",
                        "user_visibility": "0-3",
                        "reversibility": "0-3",
                        "external_dependency": "0-3",
                    },
                    "confidence": "low|medium|high",
                }
            ],
            "overall_risk_level": "low|medium|high",
            "overall_risk_score": "integer 0-15",
            "summary": "string",
        }

        return (
            "You are an expert software quality analyst. Review the following change and identify "
            "risks using the taxonomy below. Only flag risks that are actually present in the change. "
            "If the change is cosmetic or has no business impact, return an empty findings list.\n\n"
            "Risk taxonomy:\n"
            f"{json.dumps(taxonomy, indent=2, ensure_ascii=False)}\n\n"
            "Change text:\n"
            "---\n"
            f"{change_text}\n"
            "---\n\n"
            "Return a single JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "Rules:\n"
            "- risk_score must be 0-15, where 10+ is high, 5-9 is medium, and 0-4 is low.\n"
            "- overall_risk_score should be the maximum of all findings.\n"
            "- overall_risk_level must match overall_risk_score.\n"
            "- reasoning must be one sentence explaining why the risk applies.\n"
            "- Be concise and factual."
        )

    def _call_chat_completion(self, prompt: str) -> str:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": "You are a software quality analysis assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]

    def _call_chat_completion_with_usage(self, prompt: str) -> tuple[str, Dict[str, int]]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": "You are a software quality analysis assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["choices"][0]["message"]["content"]
            usage = payload.get("usage", {})
            return text, usage


def llm_finding_to_gate_match(finding: LLMRiskFinding) -> Dict[str, Any]:
    """Convert an LLM finding into the keyword-style match dictionary."""
    return {
        "id": finding.rule_id,
        "name": finding.rule_name,
        "risk_level": finding.risk_level,
        "risk_score": finding.risk_score,
        "matched_keywords": ["llm-classified"],
        "impacted_areas": list(finding.impacted_areas),
        "suggested_regression": list(finding.suggested_regression),
        "dimensions": dict(finding.dimensions),
        "source": "llm",
        "reasoning": finding.reasoning,
        "confidence": finding.confidence,
    }


def merge_llm_into_keyword_result(
    keyword_matches: List[Dict[str, Any]],
    llm_result: LLMClassificationResult,
) -> List[Dict[str, Any]]:
    """Merge LLM findings into keyword matches, keeping the highest-score signal per rule."""
    by_id: Dict[str, Dict[str, Any]] = {
        match["id"]: {
            **match,
            "matched_keywords": list(match.get("matched_keywords", [])),
            "impacted_areas": list(match.get("impacted_areas", [])),
            "suggested_regression": list(match.get("suggested_regression", [])),
            "dimensions": dict(match.get("dimensions", {})),
        }
        for match in keyword_matches
    }

    for finding in llm_result.findings:
        existing = by_id.get(finding.rule_id)
        if existing is None:
            by_id[finding.rule_id] = llm_finding_to_gate_match(finding)
        else:
            if finding.risk_score > existing["risk_score"]:
                existing["risk_score"] = finding.risk_score
                existing["risk_level"] = finding.risk_level
            # Preserve keyword evidence while enriching LLM reasoning.
            existing["reasoning"] = finding.reasoning
            existing["confidence"] = finding.confidence
            existing.setdefault("source", "hybrid")
            for area in finding.impacted_areas:
                if area not in existing["impacted_areas"]:
                    existing["impacted_areas"].append(area)
            for regression in finding.suggested_regression:
                if regression not in existing["suggested_regression"]:
                    existing["suggested_regression"].append(regression)

    return list(by_id.values())

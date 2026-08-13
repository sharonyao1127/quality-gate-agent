"""LLM-as-a-Judge for scoring quality gate output quality."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import httpx
from pydantic import BaseModel, field_validator


class JudgeScore(BaseModel):
    helpfulness: int
    actionability: int
    accuracy: int
    overall: int
    reasoning: str

    @field_validator("helpfulness", "actionability", "accuracy", "overall")
    @classmethod
    def _validate_score(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError(f"Score must be 1-5, got {value}")
        return value


@dataclass
class JudgeUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""


class LLMJudge:
    """Score a quality gate report or PR comment using an LLM judge."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self._model = model or os.getenv("QGA_JUDGE_MODEL", "gpt-4o-mini")
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self._api_key)

    def judge_report(
        self,
        change_text: str,
        report_text: str,
    ) -> tuple[Optional[JudgeScore], JudgeUsage]:
        """Score a generated report against the original change text."""
        usage = JudgeUsage(model=self._model)
        if not self._api_key:
            return None, usage

        prompt = (
            "You are an expert QA reviewer evaluating an AI-generated quality gate report.\n\n"
            "Original change text:\n"
            "---\n"
            f"{change_text}\n"
            "---\n\n"
            "Generated quality gate report:\n"
            "---\n"
            f"{report_text}\n"
            "---\n\n"
            "Score the report on a 1-5 scale for each dimension:\n"
            "- helpfulness: does it explain the risk clearly?\n"
            "- actionability: does it give concrete next steps?\n"
            "- accuracy: does it match the actual risks in the change?\n"
            "- overall: your overall judgment\n\n"
            "Return only a JSON object with keys: helpfulness, actionability, accuracy, overall, reasoning."
        )

        try:
            import time

            start = time.perf_counter()
            response_text, usage_dict = self._call(prompt)
            usage.latency_ms = (time.perf_counter() - start) * 1000
            usage.prompt_tokens = usage_dict.get("prompt_tokens", 0)
            usage.completion_tokens = usage_dict.get("completion_tokens", 0)
            usage.total_tokens = usage_dict.get("total_tokens", 0)
            score = JudgeScore.model_validate_json(response_text)
            return score, usage
        except Exception:
            return None, usage

    def _call(self, prompt: str) -> tuple[str, dict]:
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
                        {"role": "system", "content": "You are an expert QA reviewer."},
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


class MockLLMJudge:
    """Deterministic judge for testing without API keys."""

    def judge_report(
        self,
        change_text: str,
        report_text: str,
    ) -> tuple[Optional[JudgeScore], JudgeUsage]:
        score = 4
        if "HIGH RISK" in report_text or "High-risk" in report_text:
            score = 5
        if "Manual review" in report_text and "HIGH" not in report_text:
            score = 2
        return (
            JudgeScore(
                helpfulness=score,
                actionability=score,
                accuracy=score,
                overall=score,
                reasoning="Deterministic mock judgment for offline testing.",
            ),
            JudgeUsage(model="mock"),
        )

    def is_available(self) -> bool:
        return True

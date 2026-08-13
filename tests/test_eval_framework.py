from pathlib import Path

from src.eval_framework import (
    load_eval_dataset,
    evaluate_classifier,
    compare_classifiers,
    EvalSample,
    ExpectedFinding,
)
from src.gate_analyzer import load_gate_rules


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "eval_dataset" / "risk_samples.yaml"
RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"


def test_load_eval_dataset_returns_samples():
    samples = load_eval_dataset(DATASET_PATH)
    assert len(samples) == 8
    assert all(isinstance(s, EvalSample) for s in samples)
    assert any(s.name == "copywriting_only" for s in samples)


def test_evaluate_keyword_classifier():
    rules = load_gate_rules(RULES_PATH)
    samples = [
        EvalSample(
            name="high_idempotency",
            input_text="retry duplicate request_id balance deduct",
            expected_findings=[
                ExpectedFinding(rule_id="idempotency_risk", risk_level="high")
            ],
            expected_overall_level="high",
        ),
        EvalSample(
            name="low_copy",
            input_text="update help text and wording",
            expected_findings=[],
            expected_overall_level="low",
        ),
    ]

    metrics = evaluate_classifier(samples, rules, "keyword")

    assert metrics.samples_evaluated == 2
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.macro_f1 <= 1.0
    assert "idempotency_risk" in metrics.per_class


def test_compare_classifiers_without_llm():
    rules = load_gate_rules(RULES_PATH)
    samples = [
        EvalSample(
            name="async_callback",
            input_text="timeout callback delayed provider",
            expected_findings=[
                ExpectedFinding(rule_id="async_callback_risk", risk_level="high")
            ],
            expected_overall_level="high",
        )
    ]

    metrics = compare_classifiers(samples, rules, None)

    assert set(metrics.keys()) == {"keyword", "hybrid", "llm"}
    for m in metrics.values():
        assert m.samples_evaluated == 1

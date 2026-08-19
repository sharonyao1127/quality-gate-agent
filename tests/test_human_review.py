"""Tests for the closed-loop human_review module."""

import pytest

from src.eval_framework import EvalSample, ExpectedFinding
from src.human_review import (
    Correction,
    apply_label_corrections,
    collect_new_samples_from_corrections,
    load_corrections,
    summarize_corrections,
)


def _sample(name: str, level: str = "high", action: str = "human_review_required") -> EvalSample:
    return EvalSample(
        name=name,
        input_text=f"sample {name}",
        expected_findings=[],
        expected_overall_level=level,
        expected_gate_action=action,
        expected_review_required=(level == "high"),
    )


def test_load_corrections_returns_empty_when_dir_missing(tmp_path):
    assert load_corrections(tmp_path / "missing") == []


def test_load_corrections_parses_problem_lab_yaml(tmp_path):
    yaml = tmp_path / "correction.yaml"
    yaml.write_text(
        """
correction:
  correction_id: problem_lab_001
  type: missed_risk
  problem_lab_source: payment-rollout-2025
  reviewed_at: 2026-08-19
  new_sample:
    name: payment_rollback_race
    input: rollback race sample
    expected_overall_level: high
    expected_gate_action: human_review_required
    expected_review_required: true
    expected_findings: []
  note: First real-work correction.
""",
        encoding="utf-8",
    )
    corrections = load_corrections(tmp_path)

    assert len(corrections) == 1
    c = corrections[0]
    assert c.type == "missed_risk"
    assert c.problem_lab_source == "payment-rollout-2025"
    assert (c.new_sample_spec or {})["name"] == "payment_rollback_race"


def test_load_corrections_rejects_unknown_type(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
correction:
  correction_id: x
  type: opinion_piece
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be one of"):
        load_corrections(tmp_path)


def test_apply_label_corrections_overrides_level_and_action():
    samples = [_sample("a", "high"), _sample("b", "medium", "targeted_regression")]
    correction = Correction(
        correction_id="c1",
        type="label_correction",
        sample_ref="a",
        corrected_outcome={"overall_level": "low", "gate_action": "pass", "review_required": "false"},
    )

    out = apply_label_corrections(samples, [correction])

    by_name = {s.name: s for s in out}
    assert by_name["a"].expected_overall_level == "low"
    assert by_name["a"].expected_gate_action == "pass"
    assert by_name["a"].expected_review_required is False
    assert by_name["b"].expected_overall_level == "medium"


def test_apply_label_corrections_raises_on_unknown_sample_ref():
    samples = [_sample("a")]
    correction = Correction(
        correction_id="c1",
        type="label_correction",
        sample_ref="missing_sample",
        corrected_outcome={"overall_level": "low"},
    )

    with pytest.raises(ValueError, match="unknown samples"):
        apply_label_corrections(samples, [correction])


def test_collect_new_samples_from_corrections_builds_eval_samples():
    corrections = [
        Correction(
            correction_id="c1",
            type="missed_risk",
            new_sample_spec={
                "name": "rollback_race",
                "input": "rollback race input",
                "expected_overall_level": "high",
                "expected_gate_action": "human_review_required",
                "expected_review_required": True,
                "expected_findings": [
                    {
                        "rule_id": "async_callback_risk",
                        "risk_level": "high",
                        "impacted_areas": ["rollback"],
                    }
                ],
            },
        )
    ]

    samples = collect_new_samples_from_corrections(corrections)

    assert len(samples) == 1
    assert samples[0].name == "rollback_race"
    assert samples[0].expected_overall_level == "high"
    assert isinstance(samples[0].expected_findings[0], ExpectedFinding)
    assert samples[0].expected_findings[0].impacted_areas == ["rollback"]


def test_summarize_corrections_counts_three_kinds():
    corrections = [
        Correction(correction_id="c1", type="label_correction", sample_ref="a"),
        Correction(correction_id="c2", type="false_positive", sample_ref="b"),
        Correction(
            correction_id="c3",
            type="missed_risk",
            new_sample_spec={"name": "rollback_race", "input": "...", "expected_overall_level": "high"},
        ),
    ]

    summary = summarize_corrections(corrections)

    assert summary.total == 3
    assert summary.label_corrections == 1
    assert summary.false_positive_markings == 1
    assert summary.missed_risk_additions == 1
    assert summary.affected_samples == ["a", "b"]
    assert summary.new_sample_names == ["rollback_race"]


def test_default_corrections_dir_includes_first_problem_lab():
    corrections = load_corrections()

    assert len(corrections) == 1
    assert corrections[0].type == "missed_risk"
    assert corrections[0].correction_id == "problem_lab_001_payment_rollback_race"
    assert (corrections[0].new_sample_spec or {})["name"] == "payment_rollback_race_under_p99_latency"

"""Closed-loop evidence interface: human corrections become eval signal.

This module captures reviewer feedback on agent outputs and turns it into
structured eval signal. Three correction kinds are supported:

- ``label_correction``: existing sample's expected outcome is wrong; update it.
- ``missed_risk``: reviewer agrees the agent missed a risk on this kind of input.
  Adds a new sample to the eval pipeline.
- ``false_positive``: agent over-claimed a risk on this input; record so future
  rules can learn to reduce false-positive rate.

Each correction references a ``problem_lab_source`` (sanitized real-work
incident or pattern) so the closed loop is traceable back to lived
engineering experience.

Usage in scripts ::

    from src.human_review import (
        load_corrections,
        apply_label_corrections,
        collect_new_samples_from_corrections,
    )

    corrections = load_corrections()
    corrected_samples = apply_label_corrections(baseline_samples, corrections)
    extra_samples = collect_new_samples_from_corrections(corrections)
    final_samples = corrected_samples + extra_samples

Week 5 of the production agent reliability plan: closed-loop evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.eval_framework import EvalSample, ExpectedFinding


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORRECTIONS_DIR = ROOT / "eval_dataset" / "human_corrections"

VALID_TYPES = {"label_correction", "missed_risk", "false_positive"}


@dataclass
class Correction:
    """A human reviewer's correction against an agent output.

    correction_id is human-readable so it can be referenced in case studies
    and PR descriptions without exposing internal tokens.
    """

    correction_id: str
    type: str
    sample_ref: Optional[str] = None
    new_sample_spec: Optional[Dict[str, object]] = None
    original_outcome: Dict[str, str] = field(default_factory=dict)
    corrected_outcome: Dict[str, str] = field(default_factory=dict)
    note: str = ""
    problem_lab_source: str = ""
    reviewed_at: str = ""

    @property
    def is_label_change(self) -> bool:
        return self.type == "label_correction" and self.sample_ref is not None

    @property
    def is_new_sample(self) -> bool:
        return self.type == "missed_risk" and self.new_sample_spec is not None

    def to_dict(self) -> Dict[str, object]:
        return {
            "correction_id": self.correction_id,
            "type": self.type,
            "sample_ref": self.sample_ref,
            "new_sample": self.new_sample_spec,
            "original_outcome": dict(self.original_outcome),
            "corrected_outcome": dict(self.corrected_outcome),
            "problem_lab_source": self.problem_lab_source,
            "reviewed_at": self.reviewed_at,
            "note_preview": _note_preview(self.note),
        }


@dataclass
class CorrectionSummary:
    """Aggregated counts and per-sample impact for a set of corrections."""

    total: int
    label_corrections: int
    missed_risk_additions: int
    false_positive_markings: int
    affected_samples: List[str]
    new_sample_names: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "total": self.total,
            "label_corrections": self.label_corrections,
            "missed_risk_additions": self.missed_risk_additions,
            "false_positive_markings": self.false_positive_markings,
            "affected_samples": list(self.affected_samples),
            "new_sample_names": list(self.new_sample_names),
        }


def load_corrections(corrections_dir: Path = DEFAULT_CORRECTIONS_DIR) -> List[Correction]:
    """Load correction YAML files from a directory."""
    if not corrections_dir.exists():
        return []

    corrections: List[Correction] = []
    for path in sorted(corrections_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw:
            continue
        entry = raw.get("correction") if isinstance(raw, dict) else None
        if entry is None:
            continue
        corrections.append(_parse_correction(entry, source=str(path.name)))
    return corrections


def apply_label_corrections(
    samples: List[EvalSample],
    corrections: List[Correction],
) -> List[EvalSample]:
    """Return a sample list with label_correction entries applied.

    Corrections whose ``sample_ref`` does not match a real sample are dropped,
    not silently ignored, so we always surface mis-typed corrections.
    """
    by_name = {correction.sample_ref: correction for correction in corrections if correction.is_label_change}
    matched_names = set()
    out: List[EvalSample] = []
    for sample in samples:
        correction = by_name.get(sample.name)
        if correction is None:
            out.append(sample)
            continue
        matched_names.add(sample.name)
        out.append(_apply_correction(sample, correction))
    unmatched = set(by_name) - matched_names
    if unmatched:
        raise ValueError(
            f"label_correction references unknown samples: {sorted(unmatched)}"
        )
    return out


def collect_new_samples_from_corrections(
    corrections: List[Correction],
) -> List[EvalSample]:
    """Convert missed_risk corrections into EvalSample entries."""
    samples: List[EvalSample] = []
    for correction in corrections:
        if not correction.is_new_sample:
            continue
        spec = correction.new_sample_spec or {}
        findings = [
            ExpectedFinding(
                rule_id=f["rule_id"],
                risk_level=f["risk_level"],
                impacted_areas=list(f.get("impacted_areas", [])),
            )
            for f in spec.get("expected_findings", [])
        ]
        samples.append(
            EvalSample(
                name=spec["name"],
                input_text=spec["input"],
                expected_findings=findings,
                expected_overall_level=spec["expected_overall_level"],
                expected_gate_action=spec.get("expected_gate_action", ""),
                expected_review_required=spec.get("expected_review_required"),
            )
        )
    return samples


def summarize_corrections(corrections: List[Correction]) -> CorrectionSummary:
    """Aggregate counts and surfaces for reporting."""
    label_corrections = sum(1 for c in corrections if c.is_label_change)
    missed_risk = sum(1 for c in corrections if c.is_new_sample)
    false_positive = sum(1 for c in corrections if c.type == "false_positive")
    affected = sorted({c.sample_ref for c in corrections if c.sample_ref})
    new_names = sorted(
        (c.new_sample_spec or {}).get("name", "") for c in corrections if c.is_new_sample
    )
    return CorrectionSummary(
        total=len(corrections),
        label_corrections=label_corrections,
        missed_risk_additions=missed_risk,
        false_positive_markings=false_positive,
        affected_samples=[name for name in affected if name],
        new_sample_names=[name for name in new_names if name],
    )


def _parse_correction(entry: Dict[str, object], source: str) -> Correction:
    ctype = str(entry.get("type", ""))
    if ctype not in VALID_TYPES:
        raise ValueError(
            f"{source}: correction.type must be one of {sorted(VALID_TYPES)}, got {ctype!r}"
        )
    new_sample_spec = entry.get("new_sample") if ctype == "missed_risk" else None
    if ctype == "missed_risk" and not isinstance(new_sample_spec, dict):
        raise ValueError(
            f"{source}: missed_risk correction must include a 'new_sample' block"
        )

    original = entry.get("original_outcome") or {}
    corrected = entry.get("corrected_outcome") or {}

    return Correction(
        correction_id=str(entry.get("correction_id", source)),
        type=ctype,
        sample_ref=entry.get("sample_ref"),
        new_sample_spec=new_sample_spec,
        original_outcome={k: str(v) for k, v in (original or {}).items()},
        corrected_outcome={k: str(v) for k, v in (corrected or {}).items()},
        note=str(entry.get("note", "")),
        problem_lab_source=str(entry.get("problem_lab_source", "")),
        reviewed_at=str(entry.get("reviewed_at", "")),
    )


def _apply_correction(sample: EvalSample, correction: Correction) -> EvalSample:
    """Build a new EvalSample using corrected_outcome values."""
    corrected = correction.corrected_outcome
    return EvalSample(
        name=sample.name,
        input_text=sample.input_text,
        expected_findings=sample.expected_findings,
        expected_overall_level=corrected.get("overall_level", sample.expected_overall_level),
        expected_gate_action=corrected.get("gate_action", sample.expected_gate_action),
        expected_review_required=_truthy_or_none(
            corrected.get("review_required", sample.expected_review_required)
        ),
    )


def _truthy_or_none(value: object) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _note_preview(note: str, max_length: int = 80) -> str:
    compact = " ".join(note.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "\u2026"

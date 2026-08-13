"""Structured evaluation framework for quality gate classifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.gate_analyzer import analyze_change, GateAnalysisResult, load_gate_rules
from src.llm_risk_classifier import LLMRiskClassifier


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
DEFAULT_DATASET_PATH = ROOT / "eval_dataset" / "risk_samples.yaml"


@dataclass
class ExpectedFinding:
    rule_id: str
    risk_level: str
    impacted_areas: List[str] = field(default_factory=list)


@dataclass
class EvalSample:
    name: str
    input_text: str
    expected_findings: List[ExpectedFinding]
    expected_overall_level: str


@dataclass
class ClassMetrics:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass
class EvalMetrics:
    accuracy: float
    macro_f1: float
    per_class: Dict[str, ClassMetrics]
    samples_evaluated: int
    classifier_mode: str


def load_eval_dataset(path: Path) -> List[EvalSample]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    samples: List[EvalSample] = []
    for item in raw.get("samples", []):
        findings = [
            ExpectedFinding(
                rule_id=f["rule_id"],
                risk_level=f["risk_level"],
                impacted_areas=f.get("impacted_areas", []),
            )
            for f in item.get("expected_findings", [])
        ]
        samples.append(
            EvalSample(
                name=item["name"],
                input_text=item["input"],
                expected_findings=findings,
                expected_overall_level=item["expected_overall_level"],
            )
        )
    return samples


def _rule_id_set(result: GateAnalysisResult) -> set[str]:
    return {match.id for match in result.matches}


def _level_correct(result: GateAnalysisResult, sample: EvalSample) -> bool:
    return result.overall_risk_level == sample.expected_overall_level


def evaluate_classifier(
    samples: List[EvalSample],
    rules: List[Dict[str, object]],
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
) -> EvalMetrics:
    """Evaluate a classifier against a labeled dataset.

    Computes per-rule precision/recall/F1 and overall accuracy/macro-F1.
    """
    per_class_counts: Dict[str, Dict[str, int]] = {}
    correct_level_count = 0

    for sample in samples:
        result = analyze_change(
            sample.input_text,
            rules,
            input_type="eval",
            llm_classifier=llm_classifier,
            classifier_mode=classifier_mode,
        )

        if _level_correct(result, sample):
            correct_level_count += 1

        expected_ids = {f.rule_id for f in sample.expected_findings}
        actual_ids = _rule_id_set(result)

        for rule_id in expected_ids:
            per_class_counts.setdefault(rule_id, {"tp": 0, "fp": 0, "fn": 0})
            if rule_id in actual_ids:
                per_class_counts[rule_id]["tp"] += 1
            else:
                per_class_counts[rule_id]["fn"] += 1

        for rule_id in actual_ids:
            if rule_id not in expected_ids:
                per_class_counts.setdefault(rule_id, {"tp": 0, "fp": 0, "fn": 0})
                per_class_counts[rule_id]["fp"] += 1

    per_class: Dict[str, ClassMetrics] = {}
    f1_scores: List[float] = []
    for rule_id, counts in per_class_counts.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        per_class[rule_id] = ClassMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            tp=tp,
            fp=fp,
            fn=fn,
        )
        f1_scores.append(f1)

    accuracy = correct_level_count / len(samples) if samples else 0.0
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return EvalMetrics(
        accuracy=accuracy,
        macro_f1=macro_f1,
        per_class=per_class,
        samples_evaluated=len(samples),
        classifier_mode=classifier_mode,
    )


def compare_classifiers(
    samples: List[EvalSample],
    rules: List[Dict[str, object]],
    llm_classifier: Optional[LLMRiskClassifier] = None,
) -> Dict[str, EvalMetrics]:
    """Compare keyword, hybrid, and llm classifiers on the same dataset."""
    return {
        "keyword": evaluate_classifier(samples, rules, "keyword"),
        "hybrid": evaluate_classifier(samples, rules, "hybrid", llm_classifier),
        "llm": evaluate_classifier(samples, rules, "llm", llm_classifier),
    }


def generate_eval_report(metrics: Dict[str, EvalMetrics]) -> str:
    """Generate a Markdown evaluation report comparing classifiers."""
    lines = [
        "# Quality Gate Classifier Evaluation",
        "",
        "This report compares keyword, hybrid, and LLM-based risk classification on a labeled dataset.",
        "",
        "## Overall Metrics",
        "",
        "| Classifier | Accuracy | Macro F1 | Samples |",
        "|---|---:|---:|---:|",
    ]
    for mode in ["keyword", "hybrid", "llm"]:
        m = metrics[mode]
        lines.append(
            f"| {mode} | {m.accuracy:.2%} | {m.macro_f1:.2%} | {m.samples_evaluated} |"
        )

    lines.extend(["", "## Per-Rule Metrics", ""])

    for mode in ["keyword", "hybrid", "llm"]:
        m = metrics[mode]
        lines.append(f"### {mode}")
        lines.append("")
        lines.append("| Rule | Precision | Recall | F1 | TP | FP | FN |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        if not m.per_class:
            lines.append("| No rules evaluated | - | - | - | - | - | - |")
        for rule_id, cm in sorted(m.per_class.items()):
            lines.append(
                f"| {rule_id} | {cm.precision:.2%} | {cm.recall:.2%} | {cm.f1:.2%} | "
                f"{cm.tp} | {cm.fp} | {cm.fn} |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    rules = load_gate_rules(str(DEFAULT_RULES_PATH))
    samples = load_eval_dataset(DEFAULT_DATASET_PATH)
    llm_classifier = LLMRiskClassifier()
    metrics = compare_classifiers(samples, rules, llm_classifier)
    report = generate_eval_report(metrics)
    output_path = ROOT / "outputs" / "classifier_eval_report.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()

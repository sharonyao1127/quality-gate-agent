"""End-to-end runtime comparison: native vs LangGraph.

Runs the labeled eval dataset through both runtimes and compares
accuracy, decision correctness, latency, and output consistency.

Usage::

    python3 -m src.runtime_eval
    python3 -m src.runtime_eval --output outputs/runtime_eval_report.md
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.agent_workflow import run_agent_workflow
from src.agent_workflow import AgentWorkflowResult
from src.eval_framework import EvalSample, load_eval_dataset
from src.gate_analyzer import load_gate_rules
from src.human_review import (
    Correction,
    apply_label_corrections,
    collect_new_samples_from_corrections,
    load_corrections,
    summarize_corrections,
)
from src.langgraph_workflow import run_langgraph_workflow
from src.llm_risk_classifier import LLMRiskClassifier


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
DEFAULT_DATASET_PATH = ROOT / "eval_dataset" / "risk_samples.yaml"
DEFAULT_OUTPUT_PATH = ROOT / "outputs" / "runtime_eval_report.md"
DEFAULT_EVIDENCE_LOOP_OUTPUT_PATH = ROOT / "outputs" / "evidence_loop_report.md"


@dataclass
class RuntimeSampleResult:
    """Result of running one sample through one runtime."""

    sample_name: str
    runtime: str  # "native" or "langgraph"
    risk_level: str
    gate_action: str
    review_required: bool
    latency_ms: float
    span_count: int
    report_preview: str
    level_correct: bool
    action_correct: bool


@dataclass
class RuntimeMetrics:
    """Aggregated metrics for one runtime across all samples."""

    runtime: str
    samples_evaluated: int
    level_accuracy: float
    decision_accuracy: float
    avg_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    avg_span_count: float
    sample_results: List[RuntimeSampleResult] = field(default_factory=list)


@dataclass
class ConsistencyResult:
    """Per-sample comparison between native and langgraph."""

    sample_name: str
    native_level: str
    langgraph_level: str
    level_consistent: bool
    native_action: str
    langgraph_action: str
    action_consistent: bool
    native_latency_ms: float
    langgraph_latency_ms: float
    latency_diff_ms: float


@dataclass
class EvalReport:
    """Full evaluation report."""

    native_metrics: RuntimeMetrics
    langgraph_metrics: RuntimeMetrics
    consistency: List[ConsistencyResult]
    consistent_samples: int
    total_samples: int


@dataclass
class EvidenceLoopReport:
    """Comparison of before vs after applying human corrections.

    The same eval pipeline runs twice: first on the original labeled
    samples, then on the post-correction pipeline (label overrides applied
    plus any missed_risk additions). The delta is what the closed loop
    teaches the dataset.
    """

    baseline: EvalReport
    post_correction: EvalReport
    corrections_summary: Dict[str, object]
    baseline_sample_count: int
    post_sample_count: int


def _run_sample(
    sample: EvalSample,
    rules: List[Dict],
    runtime: str,
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
) -> RuntimeSampleResult:
    """Run one sample through one runtime and measure latency."""
    start = time.perf_counter()

    if runtime == "langgraph":
        result = run_langgraph_workflow(
            sample.input_text,
            rules,
            input_type="eval",
            classifier_mode=classifier_mode,
            llm_classifier=llm_classifier,
        )
    else:
        result = run_agent_workflow(
            sample.input_text,
            rules,
            input_type="eval",
            classifier_mode=classifier_mode,
            llm_classifier=llm_classifier,
        )

    latency_ms = (time.perf_counter() - start) * 1000

    expected_level = sample.expected_overall_level
    expected_action = sample.expected_gate_action or _default_action(expected_level)

    return RuntimeSampleResult(
        sample_name=sample.name,
        runtime=runtime,
        risk_level=result.analysis.overall_risk_level,
        gate_action=result.decision.action,
        review_required=result.decision.review_required,
        latency_ms=latency_ms,
        span_count=len(result.run_trace.spans),
        report_preview=result.report[:80].replace("\n", " "),
        level_correct=result.analysis.overall_risk_level == expected_level,
        action_correct=result.decision.action == expected_action,
    )


def _default_action(level: str) -> str:
    if level == "high":
        return "human_review_required"
    if level == "medium":
        return "targeted_regression"
    return "pass"


def _compute_metrics(runtime: str, results: List[RuntimeSampleResult]) -> RuntimeMetrics:
    latencies = [r.latency_ms for r in results]
    span_counts = [r.span_count for r in results]
    level_correct = sum(1 for r in results if r.level_correct)
    action_correct = sum(1 for r in results if r.action_correct)
    n = len(results)

    return RuntimeMetrics(
        runtime=runtime,
        samples_evaluated=n,
        level_accuracy=level_correct / n if n else 0.0,
        decision_accuracy=action_correct / n if n else 0.0,
        avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        p95_latency_ms=_percentile(latencies, 95) if latencies else 0.0,
        min_latency_ms=min(latencies) if latencies else 0.0,
        max_latency_ms=max(latencies) if latencies else 0.0,
        avg_span_count=statistics.mean(span_counts) if span_counts else 0.0,
        sample_results=results,
    )


def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * p / 100)
    index = min(index, len(sorted_data) - 1)
    return sorted_data[index]


def _compare_consistency(
    native_results: List[RuntimeSampleResult],
    langgraph_results: List[RuntimeSampleResult],
) -> List[ConsistencyResult]:
    native_by_name = {r.sample_name: r for r in native_results}
    langgraph_by_name = {r.sample_name: r for r in langgraph_results}

    comparisons = []
    for name in native_by_name:
        n = native_by_name[name]
        lg = langgraph_by_name.get(name)
        if lg is None:
            continue
        comparisons.append(
            ConsistencyResult(
                sample_name=name,
                native_level=n.risk_level,
                langgraph_level=lg.risk_level,
                level_consistent=n.risk_level == lg.risk_level,
                native_action=n.gate_action,
                langgraph_action=lg.gate_action,
                action_consistent=n.gate_action == lg.gate_action,
                native_latency_ms=n.latency_ms,
                langgraph_latency_ms=lg.latency_ms,
                latency_diff_ms=lg.latency_ms - n.latency_ms,
            )
        )
    return comparisons


def run_runtime_eval(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    rules_path: Path = DEFAULT_RULES_PATH,
    classifier_mode: str = "keyword",
) -> EvalReport:
    """Run the full runtime comparison evaluation."""
    samples = load_eval_dataset(dataset_path)
    rules = load_gate_rules(str(rules_path))
    llm_classifier = LLMRiskClassifier()

    native_results: List[RuntimeSampleResult] = []
    langgraph_results: List[RuntimeSampleResult] = []

    for sample in samples:
        native_results.append(
            _run_sample(sample, rules, "native", classifier_mode, llm_classifier)
        )
        langgraph_results.append(
            _run_sample(sample, rules, "langgraph", classifier_mode, llm_classifier)
        )

    native_metrics = _compute_metrics("native", native_results)
    langgraph_metrics = _compute_metrics("langgraph", langgraph_results)
    consistency = _compare_consistency(native_results, langgraph_results)
    consistent_count = sum(1 for c in consistency if c.level_consistent and c.action_consistent)

    return EvalReport(
        native_metrics=native_metrics,
        langgraph_metrics=langgraph_metrics,
        consistency=consistency,
        consistent_samples=consistent_count,
        total_samples=len(samples),
    )


def generate_runtime_eval_report(report: EvalReport) -> str:
    """Generate a Markdown report from the runtime comparison."""
    lines = [
        "# Runtime Comparison: Native vs LangGraph",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Native | LangGraph |",
        "|---|---:|---:|",
        f"| Samples | {report.native_metrics.samples_evaluated} | {report.langgraph_metrics.samples_evaluated} |",
        f"| Risk Level Accuracy | {report.native_metrics.level_accuracy:.1%} | {report.langgraph_metrics.level_accuracy:.1%} |",
        f"| Decision Accuracy | {report.native_metrics.decision_accuracy:.1%} | {report.langgraph_metrics.decision_accuracy:.1%} |",
        f"| Avg Latency | {report.native_metrics.avg_latency_ms:.1f}ms | {report.langgraph_metrics.avg_latency_ms:.1f}ms |",
        f"| P95 Latency | {report.native_metrics.p95_latency_ms:.1f}ms | {report.langgraph_metrics.p95_latency_ms:.1f}ms |",
        f"| Min Latency | {report.native_metrics.min_latency_ms:.1f}ms | {report.langgraph_metrics.min_latency_ms:.1f}ms |",
        f"| Max Latency | {report.native_metrics.max_latency_ms:.1f}ms | {report.langgraph_metrics.max_latency_ms:.1f}ms |",
        f"| Avg Span Count | {report.native_metrics.avg_span_count:.1f} | {report.langgraph_metrics.avg_span_count:.1f} |",
        "",
        "## Consistency",
        "",
        f"- Consistent samples: {report.consistent_samples} / {report.total_samples}",
        f"- Consistency rate: {report.consistent_samples / report.total_samples:.1%}" if report.total_samples else "",
        "",
        "## Per-Sample Comparison",
        "",
        "| Sample | Native Level | LG Level | Level Match | Native Action | LG Action | Action Match | Native Latency | LG Latency | Diff |",
        "|---|---|---|---|---|---|---|---:|---:|---:|",
    ]

    for c in report.consistency:
        lines.append(
            f"| {c.sample_name} | {c.native_level} | {c.langgraph_level} | "
            f"{'✓' if c.level_consistent else '✗'} | "
            f"{c.native_action} | {c.langgraph_action} | "
            f"{'✓' if c.action_consistent else '✗'} | "
            f"{c.native_latency_ms:.1f}ms | {c.langgraph_latency_ms:.1f}ms | "
            f"{c.latency_diff_ms:+.1f}ms |"
        )

    lines.extend([
        "",
        "## Analysis",
        "",
        "### Accuracy",
        "Both runtimes should produce identical risk levels and gate decisions",
        "because they share the same underlying analysis functions. Any",
        "discrepancy indicates a bug in the graph wiring or state propagation.",
        "",
        "### Latency",
        "LangGraph adds overhead from StateGraph compilation, state merging,",
        "and checkpoint management. The trade-off is durability (checkpoint",
        "recovery) and extensibility (HITL interrupt, callback hooks).",
        "",
        "### Spans",
        "Both runtimes record spans via AgentRunTracer. LangGraph may show",
        "additional callback spans when TracerCallbackHandler is used.",
    ])

    return "\n".join(lines)


def run_evidence_loop_eval(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    rules_path: Path = DEFAULT_RULES_PATH,
    classifier_mode: str = "keyword",
) -> EvidenceLoopReport:
    """Run baseline and post-correction runtime eval, return deltas.

    Applies label_corrections to baseline samples and appends missed_risk
    additions before re-running the entire pipeline through both runtimes.
    """
    from src.human_review import DEFAULT_CORRECTIONS_DIR as _corrections_dir

    baseline_samples = load_eval_dataset(dataset_path)
    rules = load_gate_rules(str(rules_path))
    llm_classifier = LLMRiskClassifier()
    corrections = load_corrections(_corrections_dir)

    baseline_report = _eval_with_samples(
        baseline_samples, rules, classifier_mode, llm_classifier
    )

    if corrections:
        adjusted = apply_label_corrections(baseline_samples, corrections)
        adjusted.extend(collect_new_samples_from_corrections(corrections))
        post_report = _eval_with_samples(
            adjusted, rules, classifier_mode, llm_classifier
        )
    else:
        post_report = baseline_report

    summary = summarize_corrections(corrections).to_dict()
    summary["by_id"] = [c.to_dict() for c in corrections]

    return EvidenceLoopReport(
        baseline=baseline_report,
        post_correction=post_report,
        corrections_summary=summary,
        baseline_sample_count=len(baseline_samples),
        post_sample_count=len(baseline_samples)
        + sum(1 for c in corrections if c.type != "label_correction"),
    )


def _eval_with_samples(
    samples: List[EvalSample],
    rules: List[Dict[str, object]],
    classifier_mode: str,
    llm_classifier: Optional[LLMRiskClassifier],
) -> EvalReport:
    """Run both runtimes over an in-memory sample list and package as EvalReport."""
    native_results: List[RuntimeSampleResult] = []
    langgraph_results: List[RuntimeSampleResult] = []

    for sample in samples:
        native_results.append(_run_sample(sample, rules, "native", classifier_mode, llm_classifier))
        langgraph_results.append(_run_sample(sample, rules, "langgraph", classifier_mode, llm_classifier))

    native_metrics = _compute_metrics("native", native_results)
    langgraph_metrics = _compute_metrics("langgraph", langgraph_results)
    consistency = _compare_consistency(native_results, langgraph_results)
    consistent_count = sum(
        1 for c in consistency if c.level_consistent and c.action_consistent
    )

    return EvalReport(
        native_metrics=native_metrics,
        langgraph_metrics=langgraph_metrics,
        consistency=consistency,
        consistent_samples=consistent_count,
        total_samples=len(samples),
    )


def generate_evidence_loop_report(report: EvidenceLoopReport) -> str:
    """Produce a Markdown report contrasting baseline vs post-correction metrics."""
    summary = report.corrections_summary
    base_n = report.baseline.native_metrics
    base_lg = report.baseline.langgraph_metrics
    post_n = report.post_correction.native_metrics
    post_lg = report.post_correction.langgraph_metrics

    def pct(value: float) -> str:
        return f"{value:.1%}"

    lines = [
        "# Evidence Loop Report: Baseline vs Post-Correction",
        "",
        "This report closes the loop between the engine and human review. The",
        "baseline run uses the original labeled samples; the post-correction run",
        "applies reviewer overrides and adds new samples drawn from real-work",
        "patterns (sanitized). The delta is the closed-loop teaching signal.",
        "",
        "## Sample Pipeline Sizes",
        "",
        f"- Baseline samples: **{report.baseline_sample_count}**",
        f"- Post-correction samples: **{report.post_sample_count}**",
        f"- Corrections loaded: **{summary.get('total', 0)}** "
        f"(label: {summary.get('label_corrections', 0)}, "
        f"missed_risk: {summary.get('missed_risk_additions', 0)}, "
        f"false_positive: {summary.get('false_positive_markings', 0)})",
        "",
        "## Metrics: Baseline",
        "",
        "| Runtime | Risk Level Acc | Decision Acc | Avg Latency | P95 Latency | Avg Spans |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Native | {pct(base_n.level_accuracy)} | {pct(base_n.decision_accuracy)} | "
        f"{base_n.avg_latency_ms:.1f}ms | {base_n.p95_latency_ms:.1f}ms | "
        f"{base_n.avg_span_count:.1f} |",
        f"| LangGraph | {pct(base_lg.level_accuracy)} | {pct(base_lg.decision_accuracy)} | "
        f"{base_lg.avg_latency_ms:.1f}ms | {base_lg.p95_latency_ms:.1f}ms | "
        f"{base_lg.avg_span_count:.1f} |",
        "",
        "## Metrics: Post-Correction",
        "",
        "| Runtime | Risk Level Acc | Decision Acc | Avg Latency | P95 Latency | Avg Spans |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Native | {pct(post_n.level_accuracy)} | {pct(post_n.decision_accuracy)} | "
        f"{post_n.avg_latency_ms:.1f}ms | {post_n.p95_latency_ms:.1f}ms | "
        f"{post_n.avg_span_count:.1f} |",
        f"| LangGraph | {pct(post_lg.level_accuracy)} | {pct(post_lg.decision_accuracy)} | "
        f"{post_lg.avg_latency_ms:.1f}ms | {post_lg.p95_latency_ms:.1f}ms | "
        f"{post_lg.avg_span_count:.1f} |",
        "",
        "## Delta",
        "",
        "| Runtime | Level Acc Δ | Decision Acc Δ | Sample Δ |",
        "|---|---:|---:|---:|",
        f"| Native | "
        f"{(post_n.level_accuracy - base_n.level_accuracy):+.1%} | "
        f"{(post_n.decision_accuracy - base_n.decision_accuracy):+.1%} | "
        f"{(report.post_sample_count - report.baseline_sample_count):+} |",
        f"| LangGraph | "
        f"{(post_lg.level_accuracy - base_lg.level_accuracy):+.1%} | "
        f"{(post_lg.decision_accuracy - base_lg.decision_accuracy):+.1%} | "
        f"{(report.post_sample_count - report.baseline_sample_count):+} |",
        "",
        "## Corrections Applied",
        "",
        f"- Affected baseline samples: "
        f"{', '.join(summary.get('affected_samples', [])) or '(none)'}",
        f"- New samples added: "
        f"{', '.join(summary.get('new_sample_names', [])) or '(none)'}",
        "",
        "## Correction Detail",
        "",
    ]

    by_id = summary.get("by_id", [])
    if not by_id:
        lines.append("- (no corrections loaded)")
    else:
        lines.append("| Correction ID | Type | Problem Lab | Sample Ref | Sample Added |")
        lines.append("|---|---|---|---|---|")
        for entry in by_id:
            sample_ref = entry.get("sample_ref") or "-"
            new_sample = (entry.get("new_sample") or {}).get("name") if isinstance(entry.get("new_sample"), dict) else "-"
            lines.append(
                f"| {entry.get('correction_id', '-')} | "
                f"{entry.get('type', '-')} | "
                f"{entry.get('problem_lab_source', '-') or '-'} | "
                f"{sample_ref} | "
                f"{new_sample or '-'} |"
            )

    lines.extend([
        "",
        "## Why This Matter",
        "",
        "Without corrections, accuracy deltas were hidden by sample noise.",
        "With corrections in the loop, every reviewer disagreement becomes a",
        "measurable teaching signal: more samples, sharper trends, and a",
        "traceable link from each delta back to a `problem_lab_source`.",
    ])

    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Runtime comparison eval")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--evidence-loop-output",
        default=str(DEFAULT_EVIDENCE_LOOP_OUTPUT_PATH),
        help="Path for the closed-loop evidence_loop_report.md.",
    )
    parser.add_argument(
        "--skip-evidence-loop",
        action="store_true",
        help="Skip writing the closed-loop report (runtime comparison only).",
    )
    parser.add_argument("--classifier", choices=["keyword", "hybrid", "llm"], default="keyword")
    args = parser.parse_args()

    report = run_runtime_eval(classifier_mode=args.classifier)
    markdown = generate_runtime_eval_report(report)

    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    print(f"\nRuntime eval report saved to {output_path}")

    if not args.skip_evidence_loop:
        evidence_report = run_evidence_loop_eval(classifier_mode=args.classifier)
        evidence_markdown = generate_evidence_loop_report(evidence_report)
        evidence_path = Path(args.evidence_loop_output)
        evidence_path.parent.mkdir(exist_ok=True)
        evidence_path.write_text(evidence_markdown, encoding="utf-8")
        print()
        print(evidence_markdown)
        print(f"\nEvidence loop report saved to {evidence_path}")


if __name__ == "__main__":
    main()

"""Tests for the runtime comparison eval module."""

from pathlib import Path

from src.runtime_eval import (
    run_evidence_loop_eval,
    run_runtime_eval,
    generate_evidence_loop_report,
    generate_runtime_eval_report,
    RuntimeMetrics,
    RuntimeSampleResult,
    ConsistencyResult,
    EvalReport,
)


def test_runtime_eval_returns_results_for_both_runtimes():
    report = run_runtime_eval()

    assert report.native_metrics.runtime == "native"
    assert report.langgraph_metrics.runtime == "langgraph"
    assert report.native_metrics.samples_evaluated > 0
    assert report.langgraph_metrics.samples_evaluated > 0
    assert report.native_metrics.samples_evaluated == report.langgraph_metrics.samples_evaluated


def test_runtime_eval_consistency_is_100_percent():
    """Both runtimes should produce identical results for all samples."""
    report = run_runtime_eval()

    assert report.consistent_samples == report.total_samples
    for c in report.consistency:
        assert c.level_consistent is True
        assert c.action_consistent is True


def test_runtime_eval_accuracy_matches_between_runtimes():
    report = run_runtime_eval()

    assert report.native_metrics.level_accuracy == report.langgraph_metrics.level_accuracy
    assert report.native_metrics.decision_accuracy == report.langgraph_metrics.decision_accuracy


def test_runtime_eval_latency_is_measured():
    report = run_runtime_eval()

    assert report.native_metrics.avg_latency_ms > 0
    assert report.langgraph_metrics.avg_latency_ms > 0
    assert report.native_metrics.p95_latency_ms >= report.native_metrics.avg_latency_ms
    assert report.langgraph_metrics.p95_latency_ms >= report.langgraph_metrics.avg_latency_ms


def test_runtime_eval_span_counts_match():
    report = run_runtime_eval()

    assert report.native_metrics.avg_span_count == report.langgraph_metrics.avg_span_count


def test_runtime_eval_report_contains_key_sections():
    report = run_runtime_eval()
    markdown = generate_runtime_eval_report(report)

    assert "# Runtime Comparison" in markdown
    assert "Native" in markdown
    assert "LangGraph" in markdown
    assert "Consistency" in markdown
    assert "Per-Sample" in markdown
    assert "Accuracy" in markdown
    assert "Latency" in markdown
    assert "100.0%" in markdown


def test_runtime_eval_report_has_per_sample_rows():
    report = run_runtime_eval()
    markdown = generate_runtime_eval_report(report)

    for c in report.consistency:
        assert c.sample_name in markdown


# ---------------------------------------------------------------------------
# Evidence-loop closed-loop tests (Week 5 / v0.5)
# ---------------------------------------------------------------------------


def test_evidence_loop_eval_includes_default_correction():
    report = run_evidence_loop_eval()

    assert report.baseline_sample_count == 8
    assert report.post_sample_count >= 9  # baseline + 1 missed_risk addition
    summary = report.corrections_summary
    assert summary["total"] >= 1
    assert "payment_rollback_race_under_p99_latency" in summary["new_sample_names"]


def test_evidence_loop_eval_baseline_and_post_share_runtime_consistency():
    report = run_evidence_loop_eval()

    assert report.baseline.consistent_samples == report.baseline.total_samples
    assert report.post_correction.consistent_samples == report.post_correction.total_samples


def test_evidence_loop_report_contains_before_and_after_sections():
    report = run_evidence_loop_eval()
    markdown = generate_evidence_loop_report(report)

    assert "Evidence Loop Report" in markdown
    assert "## Metrics: Baseline" in markdown
    assert "## Metrics: Post-Correction" in markdown
    assert "## Delta" in markdown
    assert "rollout-2025" in markdown  # problem_lab_source reference
    assert "Native" in markdown and "LangGraph" in markdown


def test_evidence_loop_report_falls_back_to_baseline_when_no_corrections(tmp_path, monkeypatch):
    """Without a corrections directory, post_correction mirrors the baseline."""
    from src import human_review

    monkeypatch.setattr(human_review, "DEFAULT_CORRECTIONS_DIR", tmp_path / "no_corrections")

    report = run_evidence_loop_eval()

    assert report.corrections_summary["total"] == 0
    assert report.baseline_sample_count == report.post_sample_count
    assert report.baseline.native_metrics.level_accuracy == report.post_correction.native_metrics.level_accuracy

"""Tests for the runtime comparison eval module."""

from pathlib import Path

from src.runtime_eval import (
    run_runtime_eval,
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

"""Tests for the LangGraph-based Quality Gate workflow runtime.

These tests mirror ``test_agent_workflow.py`` to verify that both runtimes
produce equivalent results.
"""

import pytest

from src.agent_workflow import AgentWorkflowError
from src.langgraph_workflow import run_langgraph_workflow


def _high_risk_rules():
    return [
        {
            "id": "async_callback_risk",
            "name": "Async Callback Risk",
            "keywords": ["provider", "callback", "timeout"],
            "dimensions": {
                "business_impact": 3,
                "data_consistency": 3,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 3,
            },
            "impacted_areas": ["external provider callback"],
            "suggested_regression": ["Simulate provider timeout."],
        }
    ]


def _mixed_risk_rules():
    return _high_risk_rules() + [
        {
            "id": "status_consistency_risk",
            "name": "Status Consistency Risk",
            "keywords": ["status", "frontend", "backend", "display", "pending"],
            "dimensions": {
                "business_impact": 2,
                "data_consistency": 1,
                "user_visibility": 2,
                "reversibility": 2,
                "external_dependency": 1,
            },
            "impacted_areas": ["frontend/backend consistency"],
            "suggested_regression": ["Verify frontend display for each backend status."],
        }
    ]


def test_langgraph_workflow_returns_same_result_shape_as_native():
    workflow = run_langgraph_workflow(
        "Provider callback timeout can update transaction status.",
        _high_risk_rules(),
        input_type="api_change",
    )

    assert workflow.analysis.overall_risk_level == "high"
    assert workflow.decision.action == "human_review_required"
    assert workflow.report.startswith("# Quality Gate Report")
    assert "Quality Gate Result" in workflow.pr_comment
    assert workflow.regression_pack["risk_level"] == "high"


def test_langgraph_workflow_records_spans_in_trace():
    workflow = run_langgraph_workflow(
        "Provider callback timeout can update transaction status.",
        _high_risk_rules(),
        input_type="api_change",
    )

    assert workflow.run_trace.status == "ok"
    assert workflow.run_trace.input_type == "api_change"
    span_names = [span.name for span in workflow.run_trace.spans]
    assert span_names == [
        "classify_risk",
        "validate_schema",
        "decide_gate",
        "generate_outputs",
    ]


def test_langgraph_workflow_audit_steps_match_native():
    workflow = run_langgraph_workflow(
        "Provider callback timeout can update transaction status.",
        _high_risk_rules(),
        input_type="api_change",
    )

    assert workflow.audit_steps == [
        "load_change_context",
        "classify_risk:keyword",
        "validate_schema",
        "decide_gate:human_review_required",
        "generate_outputs",
    ]


def test_langgraph_workflow_handles_medium_risk_input():
    """Medium-risk input with good confidence should route to targeted_regression."""
    workflow = run_langgraph_workflow(
        "Backend status display logic added a new pending value. "
        "Frontend display should handle the new user-facing state.",
        _mixed_risk_rules(),
        input_type="generic",
    )

    assert workflow.analysis.overall_risk_level == "medium"
    assert workflow.decision.action == "targeted_regression"
    assert workflow.run_trace.status == "ok"


def test_langgraph_workflow_preserves_trace_on_error():
    rules = [
        {
            "id": "bad_dimension",
            "name": "Bad Dimension",
            "keywords": ["callback"],
            "dimensions": {"unknown_dimension": 3},
        }
    ]

    with pytest.raises(AgentWorkflowError) as exc_info:
        run_langgraph_workflow("callback", rules, input_type="api_change")

    error = exc_info.value
    assert error.run_trace.status == "error"
    assert error.run_trace.completed_at is not None
    span_names = [span.name for span in error.run_trace.spans]
    assert "classify_risk" in span_names
    assert error.run_trace.spans[-1].status == "error"
    assert "ValidationError" in error.run_trace.spans[-1].error


def test_langgraph_workflow_strict_mode_blocks_high_risk():
    workflow = run_langgraph_workflow(
        "Provider callback timeout can update transaction status.",
        _high_risk_rules(),
        input_type="api_change",
        strict=True,
    )

    assert workflow.decision.action == "fail"
    assert workflow.decision.merge_blocked is True
    assert workflow.run_trace.status == "blocked"

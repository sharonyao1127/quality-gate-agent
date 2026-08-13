import pytest

from src.agent_workflow import AgentWorkflowError, run_agent_workflow


def test_run_agent_workflow_returns_decision_outputs_and_audit_steps():
    rules = [
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

    workflow = run_agent_workflow(
        "Provider callback timeout can update transaction status.",
        rules,
        input_type="api_change",
    )

    assert workflow.analysis.overall_risk_level == "high"
    assert workflow.decision.action == "human_review_required"
    assert workflow.report.startswith("# Quality Gate Report")
    assert "Quality Gate Result" in workflow.pr_comment
    assert workflow.regression_pack["risk_level"] == "high"
    assert workflow.run_trace.status == "ok"
    assert workflow.run_trace.input_type == "api_change"
    assert [span.name for span in workflow.run_trace.spans] == [
        "classify_risk",
        "validate_schema",
        "decide_gate",
        "generate_outputs",
    ]
    assert workflow.audit_steps == [
        "load_change_context",
        "classify_risk:keyword",
        "validate_schema",
        "decide_gate:human_review_required",
        "generate_outputs",
    ]


def test_run_agent_workflow_preserves_trace_when_step_raises():
    rules = [
        {
            "id": "bad_dimension",
            "name": "Bad Dimension",
            "keywords": ["callback"],
            "dimensions": {"unknown_dimension": 3},
        }
    ]

    with pytest.raises(AgentWorkflowError) as exc_info:
        run_agent_workflow("callback", rules, input_type="api_change")

    error = exc_info.value
    assert error.run_trace.status == "error"
    assert error.run_trace.completed_at is not None
    assert [span.name for span in error.run_trace.spans] == [
        "classify_risk",
        "validate_schema",
    ]
    assert error.run_trace.spans[-1].status == "error"
    assert "ValidationError" in error.run_trace.spans[-1].error

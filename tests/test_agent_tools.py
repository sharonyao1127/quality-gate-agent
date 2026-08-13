import pytest

from src.agent_tools import get_agent_tool_manifest, run_agent_tool


def test_agent_tool_manifest_exposes_json_schemas():
    manifest = get_agent_tool_manifest()

    tool_names = {tool["name"] for tool in manifest}
    assert tool_names == {
        "analyze_change",
        "analyze_prd",
        "generate_regression_pack",
        "evaluate_classifier",
    }
    analyze_change = next(tool for tool in manifest if tool["name"] == "analyze_change")
    assert analyze_change["input_schema"]["type"] == "object"
    assert "change_text" in analyze_change["input_schema"]["properties"]


def test_run_agent_tool_analyzes_change_with_structured_output():
    result = run_agent_tool(
        "analyze_change",
        {
            "change_text": "Provider callback timeout may update transaction status.",
            "input_type": "api_change",
            "business_domain": "payment",
        },
    )

    assert result["tool_name"] == "analyze_change"
    assert result["analysis"]["overall_risk_level"] == "high"
    assert result["decision"]["action"] == "human_review_required"
    assert "report" in result
    assert "pr_comment" in result
    assert "audit_steps" in result


def test_run_agent_tool_analyzes_prd_business_risk():
    result = run_agent_tool(
        "analyze_prd",
        {
            "prd_text": "Launch provider callback for payment status. Retry is still being discussed.",
            "business_domain": "payment",
        },
    )

    finding_ids = {finding["id"] for finding in result["business_risk"]["findings"]}
    assert result["tool_name"] == "analyze_prd"
    assert result["context_pack"]["source_type"] == "prd"
    assert "async_callback_gap" in finding_ids
    assert "business_risk_report" in result


def test_run_agent_tool_generates_regression_pack():
    result = run_agent_tool(
        "generate_regression_pack",
        {
            "change_text": "Duplicate request_id retry can deduct balance twice.",
            "input_type": "git_diff",
            "business_domain": "payment",
        },
    )

    assert result["tool_name"] == "generate_regression_pack"
    assert result["risk_level"] == "high"
    assert result["regression_pack"]["required_checks"]


def test_run_agent_tool_evaluates_classifier():
    result = run_agent_tool("evaluate_classifier", {"classifier_mode": "keyword"})

    assert result["tool_name"] == "evaluate_classifier"
    assert result["classifier_mode"] == "keyword"
    assert result["samples_evaluated"] > 0
    assert "per_rule" in result


def test_run_agent_tool_rejects_unknown_tool():
    with pytest.raises(ValueError, match="Unknown agent tool"):
        run_agent_tool("unknown", {})

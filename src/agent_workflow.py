from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.agent_observability import AgentRunTrace, AgentRunTracer
from src.gate_analyzer import GateAnalysisResult, analyze_change
from src.gate_decision import GateDecision, decide_gate
from src.llm_risk_classifier import LLMRiskClassifier
from src.pr_comment_generator import generate_pr_comment
from src.regression_pack_generator import generate_regression_pack
from src.report_generator import generate_gate_report
from src.schema_validator import validate_gate_analysis_result


@dataclass
class AgentWorkflowResult:
    analysis: GateAnalysisResult
    decision: GateDecision
    report: str
    pr_comment: str
    regression_pack: Dict[str, Any]
    audit_steps: List[str]
    run_trace: AgentRunTrace


def run_agent_workflow(
    change_text: str,
    rules: List[Dict[str, Any]],
    input_type: str = "generic",
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    strict: bool = False,
) -> AgentWorkflowResult:
    tracer = AgentRunTracer(input_type=input_type, classifier_mode=classifier_mode)
    audit_steps = [
        "load_change_context",
        f"classify_risk:{classifier_mode}",
    ]
    with tracer.span(
        "classify_risk",
        classifier_mode=classifier_mode,
        input_type=input_type,
        rules_count=len(rules),
    ) as span:
        analysis = analyze_change(
            change_text,
            rules,
            input_type=input_type,
            llm_classifier=llm_classifier,
            classifier_mode=classifier_mode,
        )
        span.metadata["matched_rules"] = len(analysis.matches)
        span.metadata["overall_risk_level"] = analysis.overall_risk_level

    with tracer.span("validate_schema", matches=len(analysis.matches)):
        validate_gate_analysis_result(analysis)
    audit_steps.append("validate_schema")

    with tracer.span("decide_gate", strict=strict) as span:
        decision = decide_gate(analysis, strict=strict)
        span.metadata["action"] = decision.action
        span.metadata["review_required"] = decision.review_required
        span.metadata["merge_blocked"] = decision.merge_blocked
    audit_steps.append(f"decide_gate:{decision.action}")

    with tracer.span("generate_outputs") as span:
        report = generate_gate_report(analysis)
        pr_comment = generate_pr_comment(analysis)
        regression_pack = generate_regression_pack(analysis)
        span.metadata["regression_checks"] = len(regression_pack.get("required_checks", []))
    audit_steps.append("generate_outputs")
    run_trace = tracer.finalize(status="blocked" if decision.merge_blocked else "ok")

    return AgentWorkflowResult(
        analysis=analysis,
        decision=decision,
        report=report,
        pr_comment=pr_comment,
        regression_pack=regression_pack,
        audit_steps=audit_steps,
        run_trace=run_trace,
    )

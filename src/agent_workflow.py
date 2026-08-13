from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


def run_agent_workflow(
    change_text: str,
    rules: List[Dict[str, Any]],
    input_type: str = "generic",
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    strict: bool = False,
) -> AgentWorkflowResult:
    audit_steps = [
        "load_change_context",
        f"classify_risk:{classifier_mode}",
    ]
    analysis = analyze_change(
        change_text,
        rules,
        input_type=input_type,
        llm_classifier=llm_classifier,
        classifier_mode=classifier_mode,
    )

    validate_gate_analysis_result(analysis)
    audit_steps.append("validate_schema")

    decision = decide_gate(analysis, strict=strict)
    audit_steps.append(f"decide_gate:{decision.action}")

    report = generate_gate_report(analysis)
    pr_comment = generate_pr_comment(analysis)
    regression_pack = generate_regression_pack(analysis)
    audit_steps.append("generate_outputs")

    return AgentWorkflowResult(
        analysis=analysis,
        decision=decision,
        report=report,
        pr_comment=pr_comment,
        regression_pack=regression_pack,
        audit_steps=audit_steps,
    )

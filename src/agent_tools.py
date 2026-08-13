from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.agent_workflow import run_agent_workflow
from src.business_risk_analyzer import (
    analyze_business_risk,
    business_findings_to_change_text,
    generate_business_risk_report,
)
from src.context_pack import build_context_pack
from src.eval_framework import evaluate_classifier, load_eval_dataset
from src.gate_analyzer import GateAnalysisResult, load_gate_rules
from src.llm_risk_classifier import LLMRiskClassifier


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
DEFAULT_EVAL_DATASET_PATH = ROOT / "eval_dataset" / "risk_samples.yaml"

InputType = Literal[
    "generic",
    "git_diff",
    "api_change",
    "openapi",
    "prd",
    "business_requirement",
    "release_note",
]
BusinessDomain = Literal["generic", "payment", "ads", "logistics", "healthcare", "edtech"]
ClassifierMode = Literal["keyword", "llm", "hybrid"]


class AnalyzeChangeInput(BaseModel):
    change_text: str = Field(..., min_length=1, description="Diff, API note, OpenAPI summary, or change description.")
    input_type: InputType = Field(default="generic", description="Source type for traceability and routing.")
    title: Optional[str] = Field(default=None, description="Optional human-readable change title.")
    business_domain: Optional[BusinessDomain] = Field(default=None, description="Optional domain hint.")
    classifier_mode: ClassifierMode = Field(default="keyword", description="Risk classifier strategy.")
    strict: bool = Field(default=False, description="Whether high risk should block the gate.")


class AnalyzePrdInput(BaseModel):
    prd_text: str = Field(..., min_length=1, description="Product requirement or business requirement text.")
    title: Optional[str] = Field(default=None, description="Optional PRD title override.")
    business_domain: BusinessDomain = Field(default="generic", description="Business domain for risk routing.")
    classifier_mode: ClassifierMode = Field(default="keyword", description="Risk classifier strategy.")
    strict: bool = Field(default=False, description="Whether high risk should block the gate.")


class RegressionPackInput(BaseModel):
    change_text: str = Field(..., min_length=1, description="Change context to analyze before generating checks.")
    input_type: InputType = Field(default="generic", description="Source type for traceability and routing.")
    business_domain: Optional[BusinessDomain] = Field(default=None, description="Optional domain hint.")
    classifier_mode: ClassifierMode = Field(default="keyword", description="Risk classifier strategy.")


class EvaluateClassifierInput(BaseModel):
    dataset_path: Optional[str] = Field(
        default=None,
        description="Optional path to a labeled eval dataset. Defaults to eval_dataset/risk_samples.yaml.",
    )
    classifier_mode: ClassifierMode = Field(default="keyword", description="Classifier strategy to evaluate.")


AgentToolInput = Union[AnalyzeChangeInput, AnalyzePrdInput, RegressionPackInput, EvaluateClassifierInput]


def get_agent_tool_manifest() -> List[Dict[str, Any]]:
    """Return framework-agnostic tool metadata with JSON schemas.

    The manifest is intentionally close to MCP/OpenAI tool shapes without binding
    the core engine to any one agent runtime.
    """
    return [
        _tool_manifest(
            name="analyze_change",
            description="Analyze a code, API, OpenAPI, or generic change and return risk, decision, reports, and audit steps.",
            schema=AnalyzeChangeInput,
        ),
        _tool_manifest(
            name="analyze_prd",
            description="Analyze a PRD or business requirement for release-risk gaps before implementation.",
            schema=AnalyzePrdInput,
        ),
        _tool_manifest(
            name="generate_regression_pack",
            description="Generate a structured regression checklist from change risk findings.",
            schema=RegressionPackInput,
        ),
        _tool_manifest(
            name="evaluate_classifier",
            description="Run labeled evals for a classifier mode and return accuracy plus per-rule metrics.",
            schema=EvaluateClassifierInput,
        ),
    ]


def run_agent_tool(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "analyze_change":
        return analyze_change_tool(AnalyzeChangeInput.model_validate(payload))
    if tool_name == "analyze_prd":
        return analyze_prd_tool(AnalyzePrdInput.model_validate(payload))
    if tool_name == "generate_regression_pack":
        return generate_regression_pack_tool(RegressionPackInput.model_validate(payload))
    if tool_name == "evaluate_classifier":
        return evaluate_classifier_tool(EvaluateClassifierInput.model_validate(payload))
    raise ValueError(f"Unknown agent tool: {tool_name}")


def analyze_change_tool(tool_input: AnalyzeChangeInput) -> Dict[str, Any]:
    rules = load_gate_rules(str(DEFAULT_RULES_PATH))
    context_pack = build_context_pack(
        tool_input.change_text,
        source_type=tool_input.input_type,
        title=tool_input.title,
        business_domain=tool_input.business_domain,
    )
    workflow = run_agent_workflow(
        tool_input.change_text,
        rules,
        input_type=context_pack.source_type,
        classifier_mode=tool_input.classifier_mode,
        llm_classifier=LLMRiskClassifier(),
        strict=tool_input.strict,
    )

    return {
        "tool_name": "analyze_change",
        "context_pack": context_pack.to_dict(),
        "analysis": _analysis_to_dict(workflow.analysis),
        "decision": _decision_to_dict(workflow.decision),
        "regression_pack": workflow.regression_pack,
        "report": workflow.report,
        "pr_comment": workflow.pr_comment,
        "audit_steps": workflow.audit_steps,
    }


def analyze_prd_tool(tool_input: AnalyzePrdInput) -> Dict[str, Any]:
    rules = load_gate_rules(str(DEFAULT_RULES_PATH))
    context_pack = build_context_pack(
        tool_input.prd_text,
        source_type="prd",
        title=tool_input.title,
        business_domain=tool_input.business_domain,
    )
    business_risk = analyze_business_risk(context_pack)
    business_risk_context = business_findings_to_change_text(business_risk)
    workflow_text = context_pack.to_analysis_text()
    if business_risk_context:
        workflow_text = f"{workflow_text}\n\n{business_risk_context}"

    workflow = run_agent_workflow(
        workflow_text,
        rules,
        input_type="prd",
        classifier_mode=tool_input.classifier_mode,
        llm_classifier=LLMRiskClassifier(),
        strict=tool_input.strict,
    )

    return {
        "tool_name": "analyze_prd",
        "context_pack": context_pack.to_dict(),
        "business_risk": business_risk.to_dict(),
        "analysis": _analysis_to_dict(workflow.analysis),
        "decision": _decision_to_dict(workflow.decision),
        "regression_pack": workflow.regression_pack,
        "business_risk_report": generate_business_risk_report(business_risk),
        "report": workflow.report,
        "pr_comment": workflow.pr_comment,
        "audit_steps": ["build_context_pack", "analyze_business_risk"] + workflow.audit_steps,
    }


def generate_regression_pack_tool(tool_input: RegressionPackInput) -> Dict[str, Any]:
    analysis_result = analyze_change_tool(
        AnalyzeChangeInput(
            change_text=tool_input.change_text,
            input_type=tool_input.input_type,
            business_domain=tool_input.business_domain,
            classifier_mode=tool_input.classifier_mode,
        )
    )
    return {
        "tool_name": "generate_regression_pack",
        "risk_level": analysis_result["analysis"]["overall_risk_level"],
        "risk_score": analysis_result["analysis"]["overall_risk_score"],
        "regression_pack": analysis_result["regression_pack"],
        "audit_steps": analysis_result["audit_steps"] + ["return_regression_pack"],
    }


def evaluate_classifier_tool(tool_input: EvaluateClassifierInput) -> Dict[str, Any]:
    rules = load_gate_rules(str(DEFAULT_RULES_PATH))
    dataset_path = Path(tool_input.dataset_path) if tool_input.dataset_path else DEFAULT_EVAL_DATASET_PATH
    samples = load_eval_dataset(dataset_path)
    metrics = evaluate_classifier(
        samples,
        rules,
        classifier_mode=tool_input.classifier_mode,
        llm_classifier=LLMRiskClassifier(),
    )
    return {
        "tool_name": "evaluate_classifier",
        "classifier_mode": metrics.classifier_mode,
        "accuracy": metrics.accuracy,
        "macro_f1": metrics.macro_f1,
        "samples_evaluated": metrics.samples_evaluated,
        "per_rule": {
            rule_id: {
                "precision": item.precision,
                "recall": item.recall,
                "f1": item.f1,
                "tp": item.tp,
                "fp": item.fp,
                "fn": item.fn,
            }
            for rule_id, item in sorted(metrics.per_class.items())
        },
    }


def _tool_manifest(name: str, description: str, schema: type[BaseModel]) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": schema.model_json_schema(),
    }


def _analysis_to_dict(result: GateAnalysisResult) -> Dict[str, Any]:
    return {
        "overall_risk_level": result.overall_risk_level,
        "overall_risk_score": result.overall_risk_score,
        "matches": [
            {
                "id": match.id,
                "name": match.name,
                "risk_level": match.risk_level,
                "risk_score": match.risk_score,
                "matched_keywords": list(match.matched_keywords),
                "impacted_areas": list(match.impacted_areas),
                "suggested_regression": list(match.suggested_regression),
                "dimensions": dict(match.dimensions),
                "source": match.source,
                "reasoning": match.reasoning,
            }
            for match in result.matches
        ],
        "confidence": (
            {
                "level": result.confidence.level,
                "score": result.confidence.score,
                "review_required": result.confidence.review_required,
                "reasons": list(result.confidence.reasons),
            }
            if result.confidence
            else None
        ),
        "trace": (
            {
                "input_hash": result.trace.input_hash,
                "input_type": result.trace.input_type,
                "ruleset_version": result.trace.ruleset_version,
                "total_rules_evaluated": result.trace.total_rules_evaluated,
                "rules_matched": list(result.trace.rules_matched),
                "execution_time_ms": result.trace.execution_time_ms,
                "timestamp": result.trace.timestamp,
            }
            if result.trace
            else None
        ),
    }


def _decision_to_dict(decision: Any) -> Dict[str, Any]:
    return {
        "action": decision.action,
        "review_required": decision.review_required,
        "merge_blocked": decision.merge_blocked,
        "reasons": list(decision.reasons),
        "required_followups": list(decision.required_followups),
    }

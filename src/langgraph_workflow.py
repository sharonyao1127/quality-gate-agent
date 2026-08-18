"""LangGraph-based runtime for the Quality Gate Agent workflow.

This module mirrors the native `agent_workflow.py` pipeline using LangGraph's
StateGraph, providing durable state, conditional routing, and a foundation
for checkpoint-based recovery and human-in-the-loop interrupt/resume.

The native workflow remains the default; this runtime is opt-in via
`--runtime langgraph`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.agent_observability import AgentRunTrace, AgentRunTracer
from src.agent_workflow import AgentWorkflowResult
from src.gate_analyzer import GateAnalysisResult, analyze_change
from src.gate_decision import GateDecision, decide_gate
from src.llm_risk_classifier import LLMRiskClassifier
from src.pr_comment_generator import generate_pr_comment
from src.regression_pack_generator import generate_regression_pack
from src.report_generator import generate_gate_report
from src.schema_validator import validate_gate_analysis_result


class QualityGateState(TypedDict, total=False):
    """Durable state carried through the LangGraph workflow.

    Non-serializable fields (rules, llm_classifier) are passed at invocation
    time.  For checkpoint-based recovery they would need to be reconstructed
    from config; that is a Week 2 concern.
    """

    # --- inputs ---
    change_text: str
    rules: List[Dict[str, Any]]
    input_type: str
    classifier_mode: str
    strict: bool
    llm_classifier: Optional[LLMRiskClassifier]

    # --- intermediate ---
    analysis: Optional[GateAnalysisResult]
    decision: Optional[GateDecision]

    # --- outputs ---
    report: str
    pr_comment: str
    regression_pack: Dict[str, Any]
    audit_steps: List[str]

    # --- observability ---
    run_trace: AgentRunTrace
    error: Optional[str]


def _build_graph(tracer: AgentRunTracer) -> Any:
    """Construct and compile the Quality Gate StateGraph.

    The ``tracer`` is captured via closure so each node can record spans
    without storing a non-serializable object in the graph state.
    Building per-invocation is intentional: it keeps the tracer scoped
    to a single run and avoids thread-safety issues with module-level
    state.  For hot-path reuse, a compiled graph with a configurable
    callback handler is a Week 3 optimisation.
    """

    def classify_risk_node(state: QualityGateState) -> Dict[str, Any]:
        audit_steps: List[str] = list(state.get("audit_steps", []))
        if not audit_steps:
            audit_steps = ["load_change_context", f"classify_risk:{state['classifier_mode']}"]

        with tracer.span(
            "classify_risk",
            classifier_mode=state["classifier_mode"],
            input_type=state["input_type"],
            rules_count=len(state["rules"]),
        ) as span:
            analysis = analyze_change(
                state["change_text"],
                state["rules"],
                input_type=state["input_type"],
                llm_classifier=state.get("llm_classifier"),
                classifier_mode=state["classifier_mode"],
            )
            span.metadata["matched_rules"] = len(analysis.matches)
            span.metadata["overall_risk_level"] = analysis.overall_risk_level

        return {"analysis": analysis, "audit_steps": audit_steps, "run_trace": tracer.trace}

    def validate_schema_node(state: QualityGateState) -> Dict[str, Any]:
        analysis = state["analysis"]
        assert analysis is not None

        with tracer.span("validate_schema", matches=len(analysis.matches)):
            validate_gate_analysis_result(analysis)

        audit_steps = list(state.get("audit_steps", []))
        audit_steps.append("validate_schema")
        return {"audit_steps": audit_steps, "run_trace": tracer.trace}

    def decide_gate_node(state: QualityGateState) -> Dict[str, Any]:
        analysis = state["analysis"]
        assert analysis is not None

        with tracer.span("decide_gate", strict=state.get("strict", False)) as span:
            decision = decide_gate(analysis, strict=state.get("strict", False))
            span.metadata["action"] = decision.action
            span.metadata["review_required"] = decision.review_required
            span.metadata["merge_blocked"] = decision.merge_blocked

        audit_steps = list(state.get("audit_steps", []))
        audit_steps.append(f"decide_gate:{decision.action}")
        return {"decision": decision, "audit_steps": audit_steps, "run_trace": tracer.trace}

    def route_after_decision(state: QualityGateState) -> str:
        """Conditional edge: route to human_review or generate_outputs.

        For Week 1 this always routes to generate_outputs.  The routing
        logic is in place so that Week 3 can add a real interrupt node.
        """
        decision = state.get("decision")
        if decision and decision.review_required:
            # Future: return "human_review" when HITL interrupt is implemented
            return "generate_outputs"
        return "generate_outputs"

    def generate_outputs_node(state: QualityGateState) -> Dict[str, Any]:
        analysis = state["analysis"]
        assert analysis is not None

        with tracer.span("generate_outputs") as span:
            report = generate_gate_report(analysis)
            pr_comment = generate_pr_comment(analysis)
            regression_pack = generate_regression_pack(analysis)
            span.metadata["regression_checks"] = len(regression_pack.get("required_checks", []))

        audit_steps = list(state.get("audit_steps", []))
        audit_steps.append("generate_outputs")
        run_trace = tracer.finalize(
            status="blocked" if state["decision"].merge_blocked else "ok"
        )
        return {
            "report": report,
            "pr_comment": pr_comment,
            "regression_pack": regression_pack,
            "audit_steps": audit_steps,
            "run_trace": run_trace,
        }

    graph = StateGraph(QualityGateState)
    graph.add_node("classify_risk", classify_risk_node)
    graph.add_node("validate_schema", validate_schema_node)
    graph.add_node("decide_gate", decide_gate_node)
    graph.add_node("generate_outputs", generate_outputs_node)

    graph.set_entry_point("classify_risk")
    graph.add_edge("classify_risk", "validate_schema")
    graph.add_edge("validate_schema", "decide_gate")
    graph.add_conditional_edges(
        "decide_gate",
        route_after_decision,
        {
            "generate_outputs": "generate_outputs",
            # "human_review": "human_review",  # Week 3
        },
    )
    graph.add_edge("generate_outputs", END)

    return graph.compile()


def run_langgraph_workflow(
    change_text: str,
    rules: List[Dict[str, Any]],
    input_type: str = "generic",
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    strict: bool = False,
) -> AgentWorkflowResult:
    """Run the Quality Gate workflow through LangGraph's StateGraph runtime.

    Produces the same :class:`AgentWorkflowResult` shape as the native
    ``run_agent_workflow`` so callers can switch runtimes transparently.
    """
    tracer = AgentRunTracer(input_type=input_type, classifier_mode=classifier_mode)
    compiled_graph = _build_graph(tracer)

    initial_state: Dict[str, Any] = {
        "change_text": change_text,
        "rules": rules,
        "input_type": input_type,
        "classifier_mode": classifier_mode,
        "strict": strict,
        "llm_classifier": llm_classifier,
        "audit_steps": [],
    }

    try:
        final_state = compiled_graph.invoke(initial_state)
    except Exception as exc:
        run_trace = tracer.finalize(status="error")
        from src.agent_workflow import AgentWorkflowError

        raise AgentWorkflowError(
            "LangGraph workflow failed; see run_trace for captured spans.",
            run_trace,
            exc,
        ) from exc

    analysis = final_state["analysis"]
    decision = final_state["decision"]
    run_trace = final_state.get("run_trace") or tracer.finalize()

    return AgentWorkflowResult(
        analysis=analysis,
        decision=decision,
        report=final_state["report"],
        pr_comment=final_state["pr_comment"],
        regression_pack=final_state["regression_pack"],
        audit_steps=final_state["audit_steps"],
        run_trace=run_trace,
    )

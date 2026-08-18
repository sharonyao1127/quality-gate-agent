"""LangGraph-based runtime for the Quality Gate Agent workflow.

This module mirrors the native `agent_workflow.py` pipeline using LangGraph's
StateGraph, providing durable state, conditional routing, and a foundation
for checkpoint-based recovery and human-in-the-loop interrupt/resume.

The native workflow remains the default; this runtime is opt-in via
`--runtime langgraph`.

Week 2 additions:
- RetryConfig + with_retry: exponential backoff for transient failures.
- Checkpointer support (MemorySaver / SqliteSaver) for durable state.
- FailureInjector for testing retry and recovery behaviour.
- run_langgraph_workflow_resumable for checkpoint-based resume.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypedDict

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


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


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

    # --- retry metadata ---
    retry_counts: Dict[str, int]


# ---------------------------------------------------------------------------
# Retry config + wrapper
# ---------------------------------------------------------------------------


@dataclass
class RetryConfig:
    """Configuration for node-level retry with exponential backoff.

    Only transient errors (network, timeout) are retried.  Validation
    errors and logic errors are not retryable because retrying with the
    same input will produce the same result.
    """

    max_retries: int = 3
    base_delay_seconds: float = 0.05
    exponential: bool = True
    retryable_exceptions: tuple = (TimeoutError, ConnectionError, OSError)

    def delay_for_attempt(self, attempt: int) -> float:
        if self.exponential:
            return self.base_delay_seconds * (2**attempt)
        return self.base_delay_seconds


def with_retry(
    node_fn: Callable[[QualityGateState], Dict[str, Any]],
    config: RetryConfig,
    tracer: AgentRunTracer,
    span_name: str,
    injector: Optional["FailureInjector"] = None,
    fallback_fn: Optional[Callable[[QualityGateState, Exception], Dict[str, Any]]] = None,
) -> Callable[[QualityGateState], Dict[str, Any]]:
    """Wrap a node function with retry + failure injection + fallback.

    The span is created once and records retry_count in metadata.  If
    the injector is configured to fail on this node, it raises a
    retryable exception before the real function runs.

    If ``fallback_fn`` is provided and all retries are exhausted, the
    fallback is called instead of re-raising.  This enables degraded
    behaviour (e.g. keyword-only classification when LLM times out).
    """

    def wrapped(state: QualityGateState) -> Dict[str, Any]:
        retry_counts = dict(state.get("retry_counts", {}))
        with tracer.span(span_name) as span:
            last_exc: Optional[Exception] = None
            for attempt in range(config.max_retries + 1):
                try:
                    if injector:
                        injector.maybe_fail(span_name, attempt)
                    result = node_fn(state)
                    retry_counts[span_name] = attempt
                    result["retry_counts"] = retry_counts
                    span.metadata["retry_count"] = attempt
                    return result
                except config.retryable_exceptions as exc:
                    last_exc = exc
                    if attempt == config.max_retries:
                        break
                    delay = config.delay_for_attempt(attempt)
                    span.metadata.setdefault("retry_attempts", []).append(
                        {"attempt": attempt + 1, "error": str(exc), "delay_s": delay}
                    )
                    time.sleep(delay)

            # Retries exhausted - try fallback or re-raise.
            retry_counts[span_name] = config.max_retries
            span.metadata["retry_count"] = config.max_retries
            span.metadata["exhausted_retries"] = True

            if fallback_fn and last_exc is not None:
                span.metadata["fallback_used"] = True
                span.metadata["fallback_reason"] = str(last_exc)
                result = fallback_fn(state, last_exc)
                result["retry_counts"] = retry_counts
                return result

            if last_exc is not None:
                raise last_exc

    return wrapped


def with_timeout(
    node_fn: Callable[[QualityGateState], Dict[str, Any]],
    timeout_seconds: float,
) -> Callable[[QualityGateState], Dict[str, Any]]:
    """Wrap a node function with a wall-clock timeout.

    Uses a thread-based approach so it works on all platforms (signal-based
    timeout only works on Unix main threads).  If the node exceeds the
    timeout, a ``TimeoutError`` is raised, which is retryable by
    ``with_retry``.
    """
    import concurrent.futures

    def wrapped(state: QualityGateState) -> Dict[str, Any]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(node_fn, state)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Node exceeded {timeout_seconds}s timeout"
                ) from None

    return wrapped


# ---------------------------------------------------------------------------
# Failure injector (for testing)
# ---------------------------------------------------------------------------


@dataclass
class FailureInjector:
    """Inject transient failures into specific nodes for testing retry/recovery.

    Usage in tests::

        injector = FailureInjector(
            failures={"classify_risk": FailureSpec(fail_times=2, error=TimeoutError("LLM timeout"))}
        )
        # The first 2 calls to classify_risk will raise TimeoutError.
        # The 3rd call will succeed.
    """

    @dataclass
    class FailureSpec:
        fail_times: int = 1
        error: Exception = field(default_factory=lambda: TimeoutError("injected failure"))

    failures: Dict[str, "FailureInjector.FailureSpec"] = field(default_factory=dict)
    _call_counts: Dict[str, int] = field(default_factory=dict)

    def maybe_fail(self, node_name: str, attempt: int) -> None:
        spec = self.failures.get(node_name)
        if spec is None:
            return
        count = self._call_counts.get(node_name, 0)
        if count < spec.fail_times:
            self._call_counts[node_name] = count + 1
            raise spec.error


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def _build_graph(
    tracer: AgentRunTracer,
    retry_config: Optional[RetryConfig] = None,
    injector: Optional[FailureInjector] = None,
    checkpointer: Any = None,
    timeout_seconds: Optional[float] = None,
) -> Any:
    """Construct and compile the Quality Gate StateGraph.

    Parameters
    ----------
    tracer : AgentRunTracer
        Observability tracer, captured via closure.
    retry_config : RetryConfig, optional
        If provided, retryable nodes are wrapped with retry logic.
    injector : FailureInjector, optional
        If provided, injects transient failures for testing.
    checkpointer : optional
        LangGraph checkpointer (MemorySaver, SqliteSaver, etc.) for
        durable state and resume capability.
    timeout_seconds : float, optional
        Per-node wall-clock timeout.  Nodes that exceed this raise
        TimeoutError, which is retryable if retry_config is set.
    """

    def classify_risk_node(state: QualityGateState) -> Dict[str, Any]:
        audit_steps: List[str] = list(state.get("audit_steps", []))
        if not audit_steps:
            audit_steps = ["load_change_context", f"classify_risk:{state['classifier_mode']}"]

        analysis = analyze_change(
            state["change_text"],
            state["rules"],
            input_type=state["input_type"],
            llm_classifier=state.get("llm_classifier"),
            classifier_mode=state["classifier_mode"],
        )
        return {
            "analysis": analysis,
            "audit_steps": audit_steps,
            "run_trace": tracer.trace,
        }

    def classify_risk_fallback(state: QualityGateState, exc: Exception) -> Dict[str, Any]:
        """Degrade to keyword-only when LLM classification fails."""
        audit_steps: List[str] = list(state.get("audit_steps", []))
        if not audit_steps:
            audit_steps = ["load_change_context", "classify_risk:keyword(fallback)"]
        else:
            audit_steps[1] = "classify_risk:keyword(fallback)"

        analysis = analyze_change(
            state["change_text"],
            state["rules"],
            input_type=state["input_type"],
            llm_classifier=None,
            classifier_mode="keyword",
        )
        return {
            "analysis": analysis,
            "audit_steps": audit_steps,
            "run_trace": tracer.trace,
        }

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

        For Week 1-2 this always routes to generate_outputs.  Week 3
        will add a real interrupt node for HITL.
        """
        decision = state.get("decision")
        if decision and decision.review_required:
            return "generate_outputs"
        return "generate_outputs"

    def generate_outputs_node(state: QualityGateState) -> Dict[str, Any]:
        analysis = state["analysis"]
        assert analysis is not None
        report = generate_gate_report(analysis)
        pr_comment = generate_pr_comment(analysis)
        regression_pack = generate_regression_pack(analysis)
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

    def generate_outputs_fallback(state: QualityGateState, exc: Exception) -> Dict[str, Any]:
        """Produce a minimal error report when output generation fails."""
        audit_steps = list(state.get("audit_steps", []))
        audit_steps.append("generate_outputs(fallback)")
        run_trace = tracer.finalize(status="degraded")
        analysis = state.get("analysis")
        error_report = "# Quality Gate Report (Degraded)\n\nOutput generation failed. Manual review required.\n"
        return {
            "report": error_report,
            "pr_comment": "## Quality Gate Result: MANUAL REVIEW REQUIRED\n\nOutput generation failed.\n",
            "regression_pack": {"risk_level": "unknown", "required_checks": []},
            "audit_steps": audit_steps,
            "run_trace": run_trace,
        }

    # Always wrap retryable nodes with with_retry so spans are recorded
    # consistently.  When retry_config is None, use a no-retry config that
    # still creates a span and supports failure injection.
    effective_retry = retry_config or RetryConfig(max_retries=0, base_delay_seconds=0)

    classify_fn = classify_risk_node
    generate_fn = generate_outputs_node

    if timeout_seconds is not None:
        classify_fn = with_timeout(classify_fn, timeout_seconds)
        generate_fn = with_timeout(generate_fn, timeout_seconds)

    # classify_risk can have LLM timeout -> fallback to keyword-only.
    # generate_outputs can fail on I/O -> fallback to minimal report.
    # validate_schema and decide_gate are pure logic - not wrapped.
    classify_fn = with_retry(
        classify_fn, effective_retry, tracer, "classify_risk", injector,
        fallback_fn=classify_risk_fallback if retry_config else None,
    )
    generate_fn = with_retry(
        generate_fn, effective_retry, tracer, "generate_outputs", injector,
        fallback_fn=generate_outputs_fallback if retry_config else None,
    )

    graph = StateGraph(QualityGateState)
    graph.add_node("classify_risk", classify_fn)
    graph.add_node("validate_schema", validate_schema_node)
    graph.add_node("decide_gate", decide_gate_node)
    graph.add_node("generate_outputs", generate_fn)

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

    compile_kwargs: Dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return graph.compile(**compile_kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_langgraph_workflow(
    change_text: str,
    rules: List[Dict[str, Any]],
    input_type: str = "generic",
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    strict: bool = False,
    retry_config: Optional[RetryConfig] = None,
    injector: Optional[FailureInjector] = None,
    timeout_seconds: Optional[float] = None,
) -> AgentWorkflowResult:
    """Run the Quality Gate workflow through LangGraph's StateGraph runtime.

    Produces the same :class:`AgentWorkflowResult` shape as the native
    ``run_agent_workflow`` so callers can switch runtimes transparently.
    """
    tracer = AgentRunTracer(input_type=input_type, classifier_mode=classifier_mode)
    compiled_graph = _build_graph(
        tracer,
        retry_config=retry_config,
        injector=injector,
        timeout_seconds=timeout_seconds,
    )

    initial_state: Dict[str, Any] = {
        "change_text": change_text,
        "rules": rules,
        "input_type": input_type,
        "classifier_mode": classifier_mode,
        "strict": strict,
        "llm_classifier": llm_classifier,
        "audit_steps": [],
        "retry_counts": {},
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


def run_langgraph_workflow_resumable(
    change_text: str,
    rules: List[Dict[str, Any]],
    thread_id: str,
    input_type: str = "generic",
    classifier_mode: str = "keyword",
    llm_classifier: Optional[LLMRiskClassifier] = None,
    strict: bool = False,
    retry_config: Optional[RetryConfig] = None,
    injector: Optional[FailureInjector] = None,
    checkpointer: Any = None,
    resume: bool = False,
    timeout_seconds: Optional[float] = None,
) -> AgentWorkflowResult:
    """Run or resume a Quality Gate workflow with checkpoint persistence.

    Parameters
    ----------
    thread_id : str
        Unique identifier for this run.  Reusing the same thread_id
        with ``resume=True`` continues from the last checkpoint.
    checkpointer : optional
        A LangGraph checkpointer (MemorySaver, SqliteSaver, etc.).
        If None, defaults to MemorySaver.
    resume : bool
        If True, continue from the last checkpoint for this thread_id.
        If False, start a new run.
    timeout_seconds : float, optional
        Per-node wall-clock timeout.
    """
    from langgraph.checkpoint.memory import MemorySaver

    if checkpointer is None:
        checkpointer = MemorySaver()

    tracer = AgentRunTracer(
        input_type=input_type,
        classifier_mode=classifier_mode,
        run_id=thread_id,
    )
    compiled_graph = _build_graph(
        tracer,
        retry_config=retry_config,
        injector=injector,
        checkpointer=checkpointer,
        timeout_seconds=timeout_seconds,
    )

    config = {"configurable": {"thread_id": thread_id}}

    try:
        if resume:
            # Resume from last checkpoint - pass None as input.
            final_state = compiled_graph.invoke(None, config=config)
        else:
            initial_state: Dict[str, Any] = {
                "change_text": change_text,
                "rules": rules,
                "input_type": input_type,
                "classifier_mode": classifier_mode,
                "strict": strict,
                "llm_classifier": llm_classifier,
                "audit_steps": [],
                "retry_counts": {},
            }
            final_state = compiled_graph.invoke(initial_state, config=config)
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

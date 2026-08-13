from src.agent_observability import AgentRunTracer, generate_agent_run_report


def test_agent_run_tracer_records_successful_spans():
    tracer = AgentRunTracer(input_type="git_diff", classifier_mode="keyword", run_id="run_test")

    with tracer.span("load_context", source="unit_test") as span:
        span.metadata["items"] = 2

    trace = tracer.finalize()

    assert trace.run_id == "run_test"
    assert trace.status == "ok"
    assert trace.total_duration_ms >= 0
    assert trace.spans[0].name == "load_context"
    assert trace.spans[0].metadata == {"source": "unit_test", "items": 2}


def test_agent_run_tracer_records_error_status():
    tracer = AgentRunTracer(input_type="api_change", classifier_mode="keyword", run_id="run_error")

    try:
        with tracer.span("failing_step"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    trace = tracer.finalize()

    assert trace.status == "error"
    assert trace.spans[0].status == "error"
    assert trace.spans[0].error == "RuntimeError: boom"


def test_generate_agent_run_report_contains_span_table():
    tracer = AgentRunTracer(input_type="prd", classifier_mode="keyword", run_id="run_report")
    with tracer.span("analyze_prd", findings=3):
        pass
    trace = tracer.finalize()

    report = generate_agent_run_report(trace)

    assert report.startswith("# Agent Run Trace")
    assert "`run_report`" in report
    assert "| analyze_prd | ok |" in report

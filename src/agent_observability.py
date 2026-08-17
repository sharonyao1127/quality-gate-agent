from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4


@dataclass
class AgentRunSpan:
    name: str
    status: str = "ok"
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
            "metadata": self.metadata,
            "error": self.error,
            "started_at": self.started_at,
        }


@dataclass
class AgentRunTrace:
    run_id: str
    input_type: str
    classifier_mode: str
    status: str = "running"
    spans: List[AgentRunSpan] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "input_type": self.input_type,
            "classifier_mode": self.classifier_mode,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": round(self.total_duration_ms, 3),
            "spans": [span.to_dict() for span in self.spans],
        }


class AgentRunTracer:
    def __init__(
        self,
        input_type: str,
        classifier_mode: str,
        run_id: Optional[str] = None,
    ):
        self._start = perf_counter()
        self.trace = AgentRunTrace(
            run_id=run_id or f"run_{uuid4().hex[:12]}",
            input_type=input_type,
            classifier_mode=classifier_mode,
        )

    @contextmanager
    def span(self, name: str, **metadata: Any) -> Iterator[AgentRunSpan]:
        span = AgentRunSpan(name=name, metadata={key: value for key, value in metadata.items() if value is not None})
        span_start = perf_counter()
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            span.error = f"{exc.__class__.__name__}: {exc}"
            self.trace.status = "error"
            raise
        finally:
            span.duration_ms = (perf_counter() - span_start) * 1000
            self.trace.spans.append(span)

    def finalize(self, status: Optional[str] = None) -> AgentRunTrace:
        if status:
            self.trace.status = status
        elif self.trace.status == "running":
            self.trace.status = "ok"
        self.trace.completed_at = datetime.utcnow().isoformat()
        self.trace.total_duration_ms = (perf_counter() - self._start) * 1000
        return self.trace


def generate_agent_run_report(trace: AgentRunTrace) -> str:
    lines = [
        "# Agent Run Trace",
        "",
        f"- **Run ID:** `{trace.run_id}`",
        f"- **Status:** {trace.status}",
        f"- **Input Type:** {trace.input_type}",
        f"- **Classifier Mode:** {trace.classifier_mode}",
        f"- **Total Duration:** {trace.total_duration_ms:.2f}ms",
        "",
        "## Spans",
        "",
        "| Step | Status | Duration | Metadata |",
        "|---|---|---:|---|",
    ]

    for span in trace.spans:
        metadata = ", ".join(f"{key}={value}" for key, value in sorted(span.metadata.items())) or "-"
        lines.append(f"| {span.name} | {span.status} | {span.duration_ms:.2f}ms | {metadata} |")

    return "\n".join(lines)

# Agent Tool Interface

Quality Gate Agent exposes a framework-agnostic tool interface for agent runtimes.

The goal is to keep the core engine independent from any single framework while still making it easy to wrap with MCP, OpenAI Agents SDK, LangGraph, CI bots, or internal workflow systems.

## Tools

The current manifest includes four tools:

- `analyze_change`: analyzes code, API, OpenAPI, or generic change context.
- `analyze_prd`: analyzes PRD/business requirement risk before implementation.
- `generate_regression_pack`: returns a structured regression checklist from risk findings.
- `evaluate_classifier`: runs labeled classifier evals and returns accuracy, macro-F1, and per-rule metrics.

## Usage

```python
from src.agent_tools import get_agent_tool_manifest, run_agent_tool

manifest = get_agent_tool_manifest()

result = run_agent_tool(
    "analyze_change",
    {
        "change_text": "Provider callback timeout may update transaction status.",
        "input_type": "api_change",
        "business_domain": "payment",
    },
)

print(result["decision"]["action"])
```

## Design

Each tool has a Pydantic input schema. The manifest returns JSON Schema so external agent frameworks can validate arguments before calling the tool.

This provides a stable boundary:

- Agent frameworks decide when to call a tool.
- Quality Gate Agent owns deterministic analysis, schema validation, traceability, reports, and evals.
- Future MCP/OpenAI/LangGraph adapters can stay thin wrappers over `run_agent_tool()`.

## Why This Matters For Enterprise Agents

Enterprise agents usually need more than prompts. They need:

- Typed tool contracts.
- Deterministic fallbacks.
- Structured outputs.
- Audit-friendly decisions.
- Eval coverage for behavior changes.
- Clear separation between public engine and private domain knowledge.

This interface is the first integration layer for those requirements.

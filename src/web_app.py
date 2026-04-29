from html import escape
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from src.gate_analyzer import analyze_change, load_gate_rules
from src.pr_comment_generator import generate_pr_comment


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"

app = FastAPI(title="Quality Gate Agent UI", version="0.1.0")


def _render_page(
    change_summary: str = "",
    risk_score: int | None = None,
    impacted_areas: List[str] | None = None,
    pr_comment: str = "",
) -> str:
    impacted_areas = impacted_areas or []
    escaped_summary = escape(change_summary)
    escaped_comment = escape(pr_comment)
    impacted_html = "".join(f"<li>{escape(area)}</li>" for area in impacted_areas)
    result_html = ""

    if risk_score is not None:
        result_html = f"""
        <section class=\"card\">
          <h2>Analyze Result</h2>
          <p><strong>Risk Score:</strong> {risk_score} / 15</p>
          <h3>Impacted Areas</h3>
          <ul>{impacted_html or '<li>No impacted areas detected by current rules.</li>'}</ul>
          <h3>PR Comment</h3>
          <pre>{escaped_comment}</pre>
        </section>
        """

    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Quality Gate Agent UI</title>
        <style>
          body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; }}
          .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-top: 16px; }}
          textarea {{ width: 100%; min-height: 180px; font-family: monospace; }}
          button {{ margin-top: 12px; padding: 8px 14px; cursor: pointer; }}
          pre {{ background: #f7f7f7; padding: 12px; overflow-x: auto; white-space: pre-wrap; }}
        </style>
      </head>
      <body>
        <h1>Quality Gate Agent</h1>
        <p>Input API change summary, click Analyze, get Risk Score / Impacted Areas / PR Comment.</p>
        <form method=\"post\" action=\"/analyze\" class=\"card\">
          <label for=\"change_summary\"><strong>API Change Summary</strong></label>
          <textarea id=\"change_summary\" name=\"change_summary\" placeholder=\"Paste API change summary here...\">{escaped_summary}</textarea>
          <br />
          <button type=\"submit\">Analyze</button>
        </form>
        {result_html}
      </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _render_page()


@app.post("/analyze", response_class=HTMLResponse)
def analyze(change_summary: str = Form(...)) -> str:
    rules = load_gate_rules(str(RULES_PATH))
    result = analyze_change(change_summary, rules)
    impacted_areas = sorted({area for match in result.matches for area in match.impacted_areas})
    pr_comment = generate_pr_comment(result)

    return _render_page(
        change_summary=change_summary,
        risk_score=result.overall_risk_score,
        impacted_areas=impacted_areas,
        pr_comment=pr_comment,
    )


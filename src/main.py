import argparse
from pathlib import Path
import yaml

from src.change_loader import load_change_text
from src.gate_analyzer import analyze_change, load_gate_rules
from src.report_generator import generate_gate_report
from src.pr_comment_generator import generate_pr_comment
from src.eval_runner import run_eval_cases, generate_eval_summary
from src.eval_runner import run_ai_pr_review_eval_cases, generate_ai_pr_review_eval_summary
from src.regression_pack_generator import generate_regression_pack


ROOT = Path(__file__).resolve().parents[1]
CHANGE_PATHS = [
    str(ROOT / "examples" / "diffs" / "payment_status_change.diff"),
    str(ROOT / "examples" / "api_changes" / "payment_api_change.md"),
    str(ROOT / "examples" / "openapi" / "openapi_change_summary.md"),
]
RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality Gate Agent")
    parser.add_argument("--gate-mode", choices=["report", "strict"], default="report")
    args = parser.parse_args()

    change_text = load_change_text(CHANGE_PATHS)
    rules = load_gate_rules(str(RULES_PATH))
    result = analyze_change(change_text, rules)

    OUTPUT_DIR.mkdir(exist_ok=True)

    report = generate_gate_report(result)
    pr_comment = generate_pr_comment(result)
    eval_summary = generate_eval_summary(run_eval_cases())
    ai_eval_summary = generate_ai_pr_review_eval_summary(run_ai_pr_review_eval_cases())
    regression_pack = generate_regression_pack(result)

    (OUTPUT_DIR / "quality_gate_report.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "pr_comment.md").write_text(pr_comment, encoding="utf-8")
    (OUTPUT_DIR / "eval_summary.md").write_text(eval_summary, encoding="utf-8")
    (OUTPUT_DIR / "ai_pr_review_eval_summary.md").write_text(ai_eval_summary, encoding="utf-8")
    (OUTPUT_DIR / "regression_pack.yaml").write_text(yaml.safe_dump(regression_pack, sort_keys=False), encoding="utf-8")

    # Export traceability report from result
    if result.trace:
        from src.traceability import TraceabilityLogger
        # Create a temporary logger to export the trace
        temp_logger = TraceabilityLogger()
        temp_logger.current_trace = result.trace
        trace_report = temp_logger.export_trace(format="markdown")
        (OUTPUT_DIR / "traceability_report.md").write_text(trace_report, encoding="utf-8")
        
        # Also export JSON version for programmatic access
        trace_json = temp_logger.export_trace(format="json")
        (OUTPUT_DIR / "traceability_report.json").write_text(trace_json, encoding="utf-8")

    print(
        f"Generated quality gate report with {len(result.matches)} matched risk rules. "
        f"Overall risk: {result.overall_risk_level} ({result.overall_risk_score}/15)"
    )
    print(f"- {OUTPUT_DIR / 'quality_gate_report.md'}")
    print(f"- {OUTPUT_DIR / 'pr_comment.md'}")
    print(f"- {OUTPUT_DIR / 'eval_summary.md'}")
    print(f"- {OUTPUT_DIR / 'ai_pr_review_eval_summary.md'}")
    print(f"- {OUTPUT_DIR / 'regression_pack.yaml'}")
    print(f"- {OUTPUT_DIR / 'traceability_report.md'}")
    print(f"- {OUTPUT_DIR / 'traceability_report.json'}")

    if args.gate_mode == "strict" and result.overall_risk_score >= 10:
        raise SystemExit("Quality gate failed: high-risk change requires manual review.")


if __name__ == "__main__":
    main()

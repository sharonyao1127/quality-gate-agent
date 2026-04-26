from pathlib import Path

from src.change_loader import load_change_text
from src.gate_analyzer import analyze_change, load_gate_rules
from src.report_generator import generate_gate_report
from src.pr_comment_generator import generate_pr_comment
from src.eval_runner import run_eval_cases, generate_eval_summary


ROOT = Path(__file__).resolve().parents[1]
CHANGE_PATHS = [
    str(ROOT / "examples" / "diffs" / "payment_status_change.diff"),
    str(ROOT / "examples" / "api_changes" / "payment_api_change.md"),
    str(ROOT / "examples" / "openapi" / "openapi_change_summary.md"),
]
RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    change_text = load_change_text(CHANGE_PATHS)
    rules = load_gate_rules(str(RULES_PATH))
    result = analyze_change(change_text, rules)

    OUTPUT_DIR.mkdir(exist_ok=True)

    report = generate_gate_report(result)
    pr_comment = generate_pr_comment(result)
    eval_summary = generate_eval_summary(run_eval_cases())

    (OUTPUT_DIR / "quality_gate_report.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "pr_comment.md").write_text(pr_comment, encoding="utf-8")
    (OUTPUT_DIR / "eval_summary.md").write_text(eval_summary, encoding="utf-8")

    print(
        f"Generated quality gate report with {len(result.matches)} matched risk rules. "
        f"Overall risk: {result.overall_risk_level} ({result.overall_risk_score}/15)"
    )
    print(f"- {OUTPUT_DIR / 'quality_gate_report.md'}")
    print(f"- {OUTPUT_DIR / 'pr_comment.md'}")
    print(f"- {OUTPUT_DIR / 'eval_summary.md'}")


if __name__ == "__main__":
    main()

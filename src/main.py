import argparse
import json
from pathlib import Path
import yaml

from src.change_loader import load_change_text
from src.gate_analyzer import analyze_change, load_gate_rules
from src.github_client import GitHubClient, GitHubPullRequest
from src.report_generator import generate_gate_report
from src.pr_comment_generator import generate_pr_comment
from src.eval_runner import run_eval_cases, generate_eval_summary
from src.eval_runner import run_ai_pr_review_eval_cases, generate_ai_pr_review_eval_summary
from src.regression_pack_generator import generate_regression_pack
from src.schema_validator import validate_gate_analysis_result
from src.llm_risk_classifier import LLMRiskClassifier
from src.llm_judge import LLMJudge, MockLLMJudge
from src.eval_framework import (
    compare_classifiers,
    generate_eval_report,
    load_eval_dataset,
)


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
    parser.add_argument(
        "--input",
        action="append",
        dest="input_paths",
        help="Path to a diff or change description. Repeat for multiple files.",
    )
    parser.add_argument(
        "--github-repository",
        help="GitHub repository in owner/name format.",
    )
    parser.add_argument("--github-pr", type=int, help="GitHub pull request number.")
    parser.add_argument(
        "--publish-comment",
        action="store_true",
        help="Create or update the quality gate comment on the GitHub pull request.",
    )
    parser.add_argument(
        "--classifier",
        choices=["keyword", "llm", "hybrid"],
        default="keyword",
        help="Risk classifier strategy. hybrid requires OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run classifier evaluation and LLM-as-a-Judge on generated reports.",
    )
    args = parser.parse_args()

    github_pull_request = None
    if args.github_pr is not None:
        if not args.github_repository or "/" not in args.github_repository:
            parser.error("--github-pr requires --github-repository owner/name.")
        owner, repo = args.github_repository.split("/", maxsplit=1)
        github_pull_request = GitHubPullRequest(owner=owner, repo=repo, number=args.github_pr)
        with GitHubClient() as github_client:
            change_text = github_client.get_pull_request_diff(github_pull_request)
        input_type = "git_diff"
    else:
        if args.publish_comment:
            parser.error("--publish-comment requires --github-pr.")
        change_text = load_change_text(args.input_paths or CHANGE_PATHS)
        input_type = "generic" if args.input_paths else "demo"

    rules = load_gate_rules(str(RULES_PATH))
    llm_classifier = LLMRiskClassifier()
    result = analyze_change(
        change_text,
        rules,
        input_type=input_type,
        llm_classifier=llm_classifier,
        classifier_mode=args.classifier,
    )
    validate_gate_analysis_result(result)

    OUTPUT_DIR.mkdir(exist_ok=True)

    report = generate_gate_report(result)
    pr_comment = generate_pr_comment(result)
    eval_summary = generate_eval_summary(run_eval_cases())
    ai_eval_summary = generate_ai_pr_review_eval_summary(run_ai_pr_review_eval_cases())
    regression_pack = generate_regression_pack(result)
    gate_result = {
        "risk_level": result.overall_risk_level,
        "risk_score": result.overall_risk_score,
        "classifier_mode": args.classifier,
        "llm_used": result.llm_result is not None,
        "matched_rules": [
            {
                "id": match.id,
                "name": match.name,
                "risk_level": match.risk_level,
                "risk_score": match.risk_score,
                "matched_keywords": match.matched_keywords,
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
            }
            if result.confidence
            else None
        ),
    }

    (OUTPUT_DIR / "quality_gate_report.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "pr_comment.md").write_text(pr_comment, encoding="utf-8")
    (OUTPUT_DIR / "eval_summary.md").write_text(eval_summary, encoding="utf-8")
    (OUTPUT_DIR / "ai_pr_review_eval_summary.md").write_text(ai_eval_summary, encoding="utf-8")
    (OUTPUT_DIR / "regression_pack.yaml").write_text(yaml.safe_dump(regression_pack, sort_keys=False), encoding="utf-8")
    (OUTPUT_DIR / "gate_result.json").write_text(
        json.dumps(gate_result, indent=2),
        encoding="utf-8",
    )

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

    if args.eval:
        eval_dataset = load_eval_dataset(ROOT / "eval_dataset" / "risk_samples.yaml")
        classifier_metrics = compare_classifiers(eval_dataset, rules, llm_classifier)
        eval_report = generate_eval_report(classifier_metrics)
        (OUTPUT_DIR / "classifier_eval_report.md").write_text(eval_report, encoding="utf-8")
        print(f"- {OUTPUT_DIR / 'classifier_eval_report.md'}")

        judge = LLMJudge() if LLMJudge().is_available() else MockLLMJudge()
        judge_score, judge_usage = judge.judge_report(change_text, report)
        judge_result = {
            "helpfulness": judge_score.helpfulness if judge_score else None,
            "actionability": judge_score.actionability if judge_score else None,
            "accuracy": judge_score.accuracy if judge_score else None,
            "overall": judge_score.overall if judge_score else None,
            "reasoning": judge_score.reasoning if judge_score else None,
            "model": judge_usage.model,
            "tokens": judge_usage.total_tokens,
            "latency_ms": judge_usage.latency_ms,
        }
        (OUTPUT_DIR / "judge_result.json").write_text(
            json.dumps(judge_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"- {OUTPUT_DIR / 'judge_result.json'}")

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
    print(f"- {OUTPUT_DIR / 'gate_result.json'}")

    if args.publish_comment and github_pull_request:
        with GitHubClient() as github_client:
            comment_url = github_client.upsert_pull_request_comment(
                github_pull_request,
                pr_comment,
            )
        print(f"- GitHub PR comment: {comment_url}")

    if args.gate_mode == "strict" and result.overall_risk_score >= 10:
        raise SystemExit("Quality gate failed: high-risk change requires manual review.")


if __name__ == "__main__":
    main()

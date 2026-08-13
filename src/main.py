import argparse
import json
from pathlib import Path
import yaml

from src.change_loader import load_change_text
from src.agent_workflow import run_agent_workflow
from src.business_risk_analyzer import (
    analyze_business_risk,
    business_findings_to_change_text,
    generate_business_risk_report,
)
from src.context_pack import build_context_pack
from src.gate_analyzer import load_gate_rules
from src.github_client import GitHubClient, GitHubPullRequest
from src.eval_runner import run_eval_cases, generate_eval_summary
from src.eval_runner import run_ai_pr_review_eval_cases, generate_ai_pr_review_eval_summary
from src.llm_risk_classifier import LLMRiskClassifier
from src.llm_judge import LLMJudge, MockLLMJudge
from src.eval_framework import (
    compare_classifiers,
    evaluate_gate_decisions,
    generate_decision_eval_report,
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
        "--input-type",
        choices=[
            "generic",
            "git_diff",
            "api_change",
            "openapi",
            "prd",
            "business_requirement",
            "release_note",
        ],
        help="Type of change context being analyzed.",
    )
    parser.add_argument("--title", help="Optional title for the change context.")
    parser.add_argument(
        "--business-domain",
        choices=["generic", "payment", "ads", "logistics", "healthcare", "edtech"],
        help="Optional business domain hint for PRD/business risk analysis.",
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
        input_type = args.input_type or ("generic" if args.input_paths else "demo")

    context_pack = build_context_pack(
        change_text,
        source_type=input_type,
        title=args.title,
        business_domain=args.business_domain,
    )
    business_risk = None
    workflow_change_text = change_text
    if context_pack.source_type in {"prd", "business_requirement", "release_note"}:
        business_risk = analyze_business_risk(context_pack)
        business_risk_context = business_findings_to_change_text(business_risk)
        workflow_change_text = context_pack.to_analysis_text()
        if business_risk_context:
            workflow_change_text = f"{workflow_change_text}\n\n{business_risk_context}"

    rules = load_gate_rules(str(RULES_PATH))
    llm_classifier = LLMRiskClassifier()
    workflow = run_agent_workflow(
        workflow_change_text,
        rules,
        input_type=context_pack.source_type,
        classifier_mode=args.classifier,
        llm_classifier=llm_classifier,
        strict=args.gate_mode == "strict",
    )
    result = workflow.analysis

    OUTPUT_DIR.mkdir(exist_ok=True)

    report = workflow.report
    pr_comment = workflow.pr_comment
    eval_summary = generate_eval_summary(run_eval_cases())
    ai_eval_summary = generate_ai_pr_review_eval_summary(run_ai_pr_review_eval_cases())
    regression_pack = workflow.regression_pack
    gate_result = {
        "risk_level": result.overall_risk_level,
        "risk_score": result.overall_risk_score,
        "classifier_mode": args.classifier,
        "llm_used": result.llm_result is not None,
        "context_pack": context_pack.to_dict(),
        "business_risk": business_risk.to_dict() if business_risk else None,
        "agent_workflow": {
            "audit_steps": workflow.audit_steps,
            "decision": {
                "action": workflow.decision.action,
                "review_required": workflow.decision.review_required,
                "merge_blocked": workflow.decision.merge_blocked,
                "reasons": workflow.decision.reasons,
                "required_followups": workflow.decision.required_followups,
            },
        },
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
    if business_risk:
        (OUTPUT_DIR / "business_risk_report.md").write_text(
            generate_business_risk_report(business_risk),
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

        decision_metrics = evaluate_gate_decisions(
            eval_dataset,
            rules,
            classifier_mode=args.classifier,
            llm_classifier=llm_classifier,
            strict=args.gate_mode == "strict",
        )
        decision_eval_report = generate_decision_eval_report(decision_metrics)
        (OUTPUT_DIR / "decision_eval_report.md").write_text(decision_eval_report, encoding="utf-8")
        (OUTPUT_DIR / "decision_eval_result.json").write_text(
            json.dumps(
                {
                    "classifier_mode": decision_metrics.classifier_mode,
                    "gate_mode": decision_metrics.gate_mode,
                    "decision_accuracy": decision_metrics.decision_accuracy,
                    "review_routing_accuracy": decision_metrics.review_routing_accuracy,
                    "high_risk_recall": decision_metrics.high_risk_recall,
                    "samples_evaluated": decision_metrics.samples_evaluated,
                    "failures": [
                        {
                            "sample_name": failure.sample_name,
                            "expected_action": failure.expected_action,
                            "actual_action": failure.actual_action,
                            "expected_review_required": failure.expected_review_required,
                            "actual_review_required": failure.actual_review_required,
                            "expected_overall_level": failure.expected_overall_level,
                            "actual_overall_level": failure.actual_overall_level,
                        }
                        for failure in decision_metrics.failures
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"- {OUTPUT_DIR / 'decision_eval_report.md'}")
        print(f"- {OUTPUT_DIR / 'decision_eval_result.json'}")

        judge = LLMJudge() if LLMJudge().is_available() else MockLLMJudge()
        judge_score, judge_usage = judge.judge_report(workflow_change_text, report)
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
    if business_risk:
        print(f"- {OUTPUT_DIR / 'business_risk_report.md'}")

    if args.publish_comment and github_pull_request:
        with GitHubClient() as github_client:
            comment_url = github_client.upsert_pull_request_comment(
                github_pull_request,
                pr_comment,
            )
        print(f"- GitHub PR comment: {comment_url}")

    if workflow.decision.merge_blocked:
        raise SystemExit("Quality gate failed: high-risk change requires manual review.")


if __name__ == "__main__":
    main()

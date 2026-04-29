from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml

from src.gate_analyzer import analyze_change, load_gate_rules


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "risk_rules" / "quality_gate_rules.yaml"
EVAL_DIR = ROOT / "eval_cases"
OUTPUT_PATH = ROOT / "outputs" / "eval_summary.md"
AI_PR_REVIEW_EVAL_DIR = EVAL_DIR / "ai_pr_review"
AI_PR_REVIEW_OUTPUT_PATH = ROOT / "outputs" / "ai_pr_review_eval_summary.md"


@dataclass
class EvalCaseResult:
    name: str
    passed: bool
    expected_level: str
    actual_level: str
    expected_min_score: int
    actual_score: int
    missing_impacted_areas: List[str]


@dataclass
class AIReviewEvalCaseResult:
    name: str
    passed: bool
    expected_result: str
    missing_risks: List[str]


def run_eval_cases() -> List[EvalCaseResult]:
    rules = load_gate_rules(str(RULES_PATH))
    results: List[EvalCaseResult] = []

    for case_path in sorted(EVAL_DIR.glob("*.yaml")):
        case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
        result = analyze_change(case["input"], rules)

        expected_areas = set(case.get("expected_impacted_areas", []))
        actual_areas = set()
        for match in result.matches:
            actual_areas.update(match.impacted_areas)

        missing = sorted(expected_areas - actual_areas)

        expected_level = case["expected_risk_level"]
        expected_min_score = int(case.get("expected_min_score", 0))

        passed = (
            result.overall_risk_level == expected_level
            and result.overall_risk_score >= expected_min_score
            and not missing
        )

        results.append(
            EvalCaseResult(
                name=case["name"],
                passed=passed,
                expected_level=expected_level,
                actual_level=result.overall_risk_level,
                expected_min_score=expected_min_score,
                actual_score=result.overall_risk_score,
                missing_impacted_areas=missing,
            )
        )

    return results


def generate_eval_summary(results: List[EvalCaseResult]) -> str:
    passed_count = sum(1 for result in results if result.passed)
    lines = [
        "# Eval Summary",
        "",
        f"Passed: {passed_count} / {len(results)}",
        "",
        "| Case | Passed | Expected Level | Actual Level | Expected Min Score | Actual Score | Missing Impacted Areas |",
        "|---|---|---|---|---:|---:|---|",
    ]

    for result in results:
        lines.append(
            f"| {result.name} | {result.passed} | {result.expected_level} | {result.actual_level} | "
            f"{result.expected_min_score} | {result.actual_score} | {', '.join(result.missing_impacted_areas) or '-'} |"
        )

    return "\n".join(lines)


def run_ai_pr_review_eval_cases() -> List[AIReviewEvalCaseResult]:
    results: List[AIReviewEvalCaseResult] = []

    if not AI_PR_REVIEW_EVAL_DIR.exists():
        return results

    for case_path in sorted(AI_PR_REVIEW_EVAL_DIR.glob("*.yaml")):
        case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
        review_text = case.get("ai_generated_review", "").lower()
        expected_risks = case.get("expected_risks", [])
        missing_risks = sorted(risk for risk in expected_risks if risk.lower() not in review_text)
        expected_result = case.get("expected_result", "pass")
        actual_result = "fail" if missing_risks else "pass"

        results.append(
            AIReviewEvalCaseResult(
                name=case["name"],
                passed=actual_result == expected_result,
                expected_result=expected_result,
                missing_risks=missing_risks,
            )
        )

    return results


def generate_ai_pr_review_eval_summary(results: List[AIReviewEvalCaseResult]) -> str:
    passed_count = sum(1 for result in results if result.passed)
    lines = [
        "# AI PR Review Eval Summary",
        "",
        f"Passed: {passed_count} / {len(results)}",
        "",
    ]

    for result in results:
        quality = "PASS" if not result.missing_risks else "FAIL"
        lines.append(f"## {result.name}")
        lines.append(f"AI Review Quality: {quality}")
        if result.missing_risks:
            lines.append("Missing Risks:")
            for risk in result.missing_risks:
                lines.append(f"- {risk}")
        else:
            lines.append("Missing Risks:\n- None")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    results = run_eval_cases()
    summary = generate_eval_summary(results)
    ai_results = run_ai_pr_review_eval_cases()
    ai_summary = generate_ai_pr_review_eval_summary(ai_results)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(summary, encoding="utf-8")
    AI_PR_REVIEW_OUTPUT_PATH.write_text(ai_summary, encoding="utf-8")

    failed = [result for result in results if not result.passed]
    print(summary)
    if ai_results:
        print()
        print(ai_summary)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

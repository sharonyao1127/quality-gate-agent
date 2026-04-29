import pytest

import src.eval_runner as eval_runner
from src.eval_runner import AIReviewEvalCaseResult, EvalCaseResult, generate_ai_pr_review_eval_summary, run_ai_pr_review_eval_cases


def test_ai_pr_review_eval_case_detects_missing_risks():
    results = run_ai_pr_review_eval_cases()

    assert results
    case = next(result for result in results if result.name == "ai_pr_review_misses_idempotency")
    assert case.missing_risks == ["async callback", "balance consistency", "idempotency"]
    assert case.passed


def test_ai_pr_review_eval_summary_contains_fail_quality_block():
    results = run_ai_pr_review_eval_cases()
    summary = generate_ai_pr_review_eval_summary(results)

    assert "AI Review Quality: FAIL" in summary
    assert "Missing Risks:" in summary


def test_eval_runner_main_exits_when_ai_eval_has_failures(monkeypatch):
    monkeypatch.setattr(
        eval_runner,
        "run_eval_cases",
        lambda: [
            EvalCaseResult(
                name="base",
                passed=True,
                expected_level="low",
                actual_level="low",
                expected_min_score=0,
                actual_score=0,
                missing_impacted_areas=[],
            )
        ],
    )
    monkeypatch.setattr(
        eval_runner,
        "run_ai_pr_review_eval_cases",
        lambda: [
            AIReviewEvalCaseResult(
                name="ai_case",
                passed=False,
                expected_result="pass",
                missing_risks=["idempotency"],
            )
        ],
    )

    with pytest.raises(SystemExit):
        eval_runner.main()

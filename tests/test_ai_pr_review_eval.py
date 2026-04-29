from src.eval_runner import generate_ai_pr_review_eval_summary, run_ai_pr_review_eval_cases


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


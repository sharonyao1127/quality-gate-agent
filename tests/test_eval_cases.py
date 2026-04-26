from src.eval_runner import run_eval_cases


def test_eval_cases_should_pass():
    results = run_eval_cases()

    assert results
    assert all(result.passed for result in results)

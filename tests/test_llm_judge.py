from src.llm_judge import LLMJudge, MockLLMJudge


def test_real_judge_not_available_without_api_key():
    judge = LLMJudge(api_key=None)
    assert judge.is_available() is False
    score, usage = judge.judge_report("change", "report")
    assert score is None
    assert usage.model != ""


def test_mock_judge_returns_score():
    judge = MockLLMJudge()
    score, usage = judge.judge_report("timeout callback", "## HIGH RISK\n- Simulate timeout")
    assert score is not None
    assert score.overall == 5
    assert usage.model == "mock"


def test_mock_judge_penalizes_weak_report():
    judge = MockLLMJudge()
    score, _ = judge.judge_report("change", "Manual review recommended.")
    assert score is not None
    assert score.overall < 5

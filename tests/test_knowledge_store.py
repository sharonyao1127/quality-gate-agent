from src.knowledge_store import (
    generate_knowledge_context,
    generate_knowledge_report,
    load_risk_patterns,
    retrieve_risk_patterns,
)


def test_load_risk_patterns_returns_public_domain_patterns():
    patterns = load_risk_patterns()

    pattern_ids = {pattern.id for pattern in patterns}
    assert "payment_async_callback_idempotency" in pattern_ids
    assert "ads_retrieval_ranking_regression" in pattern_ids
    assert "logistics_status_transition_consistency" in pattern_ids


def test_retrieve_risk_patterns_filters_by_domain_and_signals():
    result = retrieve_risk_patterns(
        "Provider callback retry timeout may update payment transaction status.",
        domain="payment",
    )

    assert result.domain == "payment"
    assert result.matched_patterns
    assert result.matched_patterns[0].id == "payment_async_callback_idempotency"
    assert all(pattern.domain == "payment" for pattern in result.matched_patterns)


def test_retrieve_risk_patterns_returns_empty_when_no_signal_matches():
    result = retrieve_risk_patterns("Update static documentation page.", domain="payment")

    assert result.matched_patterns == []


def test_retrieve_risk_patterns_does_not_match_domain_metadata_without_signals():
    result = retrieve_risk_patterns(
        "Title: Payment Copy Update\nBusiness Domain: payment\nRaw Context:\nUpdate FAQ copy.",
        domain="payment",
    )

    assert result.matched_patterns == []


def test_knowledge_retrieval_result_does_not_export_raw_query():
    result = retrieve_risk_patterns(
        "Title: Secret Payment PRD\nBusiness Domain: payment\nRaw Context:\nCustomer secret callback details",
        domain="payment",
    )

    payload = result.to_dict()

    assert "query" not in payload
    assert "query_hash" in payload
    assert "Customer secret" not in payload["query_preview"]
    assert "Raw Context" not in payload["query_preview"]


def test_generate_knowledge_context_and_report_are_actionable():
    result = retrieve_risk_patterns(
        "Ads retrieval ranking change can affect campaign traffic.",
        domain="ads",
    )

    context = generate_knowledge_context(result)
    report = generate_knowledge_report(result)

    assert "Retrieved Risk Knowledge" in context
    assert "Ads retrieval and ranking regression" in report
    assert "Recommended Checks" in report

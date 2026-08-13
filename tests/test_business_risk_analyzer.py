from src.business_risk_analyzer import (
    analyze_business_risk,
    business_findings_to_change_text,
    generate_business_risk_report,
)
from src.context_pack import build_context_pack


def test_analyze_business_risk_flags_prd_gaps_for_payment_callback():
    context = build_context_pack(
        """# Provider Payment Callback Upgrade

Business Domain: payment
Changed Components: payment callback service, transaction status updater

We will launch a new provider callback flow for payment transactions.
The provider may send delayed callback events and the transaction status will be displayed to users.
This release enables the new flow for merchants next week.
""",
        source_type="prd",
    )

    result = analyze_business_risk(context)

    finding_ids = {finding.id for finding in result.findings}
    assert "missing_acceptance_criteria" in finding_ids
    assert "async_callback_gap" in finding_ids
    assert "payment_reconciliation_gap" in finding_ids
    assert "state_transition_ambiguity" in finding_ids
    assert "rollout_observability_gap" in finding_ids
    assert result.overall_risk_level == "high"
    assert result.review_required is True


def test_analyze_business_risk_uses_acceptance_criteria_and_rollout_controls_as_negative_evidence():
    context = build_context_pack(
        """# Provider Payment Callback Upgrade

Business Domain: payment
Stakeholders: payment owner, provider integration owner

## Acceptance Criteria
- Given duplicated callbacks, the transaction update is idempotent.
- When provider callback is delayed, retry and timeout behavior keeps the transaction pending.
- Then reconciliation verifies provider response and ledger balance consistency.

The rollout uses a feature flag, dashboard monitoring, alerting, and rollback owner.
The state machine documents pending to completed and failed terminal states.
""",
        source_type="prd",
    )

    result = analyze_business_risk(context)

    finding_ids = {finding.id for finding in result.findings}
    assert "missing_acceptance_criteria" not in finding_ids
    assert "async_callback_gap" not in finding_ids
    assert "payment_reconciliation_gap" not in finding_ids
    assert "rollout_observability_gap" not in finding_ids


def test_analyze_business_risk_flags_mentions_that_are_still_unresolved():
    context = build_context_pack(
        """# Provider Payment Callback Upgrade

Business Domain: payment

## Acceptance Criteria
- Given provider timeout, retry behavior is not finalized.
- Then reconciliation ownership will be confirmed before launch.

The flow handles payment transactions and provider callbacks.
""",
        source_type="prd",
    )

    result = analyze_business_risk(context)

    findings = {finding.id: finding for finding in result.findings}
    assert "async_callback_gap" in findings
    assert "payment_reconciliation_gap" in findings
    assert "mentioned but still unresolved" in findings["async_callback_gap"].evidence[-1]
    assert "mentioned but still unresolved" in findings["payment_reconciliation_gap"].evidence[-1]


def test_business_risk_report_and_change_text_are_actionable():
    context = build_context_pack("Launch provider callback for payment status.", source_type="prd")
    result = analyze_business_risk(context)

    report = generate_business_risk_report(result)
    change_text = business_findings_to_change_text(result)

    assert report.startswith("# Business Risk Review")
    assert "Recommended checks" in report
    assert "Business Risk Findings" in change_text

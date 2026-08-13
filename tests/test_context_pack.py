from src.context_pack import build_context_pack


def test_build_context_pack_extracts_prd_metadata_from_markdown_sections():
    raw_text = """# Payment Callback PRD

Business Domain: payment

## Changed Components
- payment callback service
- ledger updater

## Stakeholders
- payment platform owner
- provider integration owner

## Acceptance Criteria
- Given duplicated callbacks, balance is deducted only once.
- When provider callback is delayed, transaction remains pending.

## Risk Hints
- external provider dependency
"""

    context = build_context_pack(raw_text, source_type="prd")

    assert context.title == "Payment Callback PRD"
    assert context.source_type == "prd"
    assert context.business_domain == "payment"
    assert context.changed_components == ["payment callback service", "ledger updater"]
    assert context.stakeholders == ["payment platform owner", "provider integration owner"]
    assert context.acceptance_criteria == [
        "Given duplicated callbacks, balance is deducted only once.",
        "When provider callback is delayed, transaction remains pending.",
    ]
    assert context.risk_hints == ["external provider dependency"]


def test_build_context_pack_infers_domain_when_label_is_missing():
    context = build_context_pack(
        "Launch refund flow with ledger balance update and provider callback.",
        source_type="business-requirement",
    )

    assert context.source_type == "business_requirement"
    assert context.business_domain == "payment"

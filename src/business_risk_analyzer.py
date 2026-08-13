from dataclasses import dataclass
import re
from typing import Callable, Iterable, List

from src.context_pack import ChangeContextPack
from src.risk_scoring import calculate_level_from_score, merge_risk_scores


@dataclass(frozen=True)
class BusinessRiskFinding:
    id: str
    name: str
    risk_level: str
    risk_score: int
    evidence: List[str]
    recommendation: List[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "evidence": list(self.evidence),
            "recommendation": list(self.recommendation),
        }


@dataclass(frozen=True)
class BusinessRiskAnalysisResult:
    source_type: str
    business_domain: str
    findings: List[BusinessRiskFinding]
    overall_risk_level: str
    overall_risk_score: int
    review_required: bool

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "business_domain": self.business_domain,
            "overall_risk_level": self.overall_risk_level,
            "overall_risk_score": self.overall_risk_score,
            "review_required": self.review_required,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class BusinessRiskRule:
    id: str
    name: str
    risk_score: int
    applies: Callable[[ChangeContextPack, str], bool]
    evidence: Callable[[ChangeContextPack, str], List[str]]
    recommendation: List[str]


def analyze_business_risk(context: ChangeContextPack) -> BusinessRiskAnalysisResult:
    text = context.to_analysis_text().lower()
    findings = [
        _to_finding(rule, context, text)
        for rule in _business_risk_rules()
        if rule.applies(context, text)
    ]

    overall_score = merge_risk_scores(finding.risk_score for finding in findings)
    overall_level = calculate_level_from_score(overall_score)
    review_required = overall_score >= 5 or any(finding.risk_level == "high" for finding in findings)

    return BusinessRiskAnalysisResult(
        source_type=context.source_type,
        business_domain=context.business_domain,
        findings=findings,
        overall_risk_level=overall_level,
        overall_risk_score=overall_score,
        review_required=review_required,
    )


def generate_business_risk_report(result: BusinessRiskAnalysisResult) -> str:
    lines = [
        "# Business Risk Review",
        "",
        f"## Overall Risk Level: {result.overall_risk_level.upper()}",
        "",
        f"## Overall Risk Score: {result.overall_risk_score} / 15",
        "",
        f"- **Source Type:** {result.source_type}",
        f"- **Business Domain:** {result.business_domain}",
        f"- **Human Review Required:** {'yes' if result.review_required else 'no'}",
        "",
        "## Findings",
        "",
    ]

    if not result.findings:
        lines.append("- No business risk findings detected by current rules.")
    else:
        for finding in result.findings:
            lines.extend(
                [
                    f"### {finding.name}",
                    f"- **Risk:** {finding.risk_level} ({finding.risk_score}/15)",
                    f"- **Evidence:** {', '.join(finding.evidence)}",
                    "- **Recommended checks:**",
                ]
            )
            for item in finding.recommendation:
                lines.append(f"  - {item}")
            lines.append("")

    lines.extend(
        [
            "## How To Use This",
            "",
            "- Treat this as a pre-code review for product, business, and release-risk gaps.",
            "- Convert each finding into acceptance criteria, regression checks, or rollout tasks before implementation.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def business_findings_to_change_text(result: BusinessRiskAnalysisResult) -> str:
    if not result.findings:
        return ""

    lines = [
        "Business Risk Findings:",
        f"Overall Business Risk: {result.overall_risk_level} ({result.overall_risk_score}/15)",
    ]
    for finding in result.findings:
        lines.extend(
            [
                f"- {finding.name}: {finding.risk_level} ({finding.risk_score}/15)",
                f"  Evidence: {', '.join(finding.evidence)}",
                f"  Recommended checks: {'; '.join(finding.recommendation)}",
            ]
        )
    return "\n".join(lines)


def _to_finding(rule: BusinessRiskRule, context: ChangeContextPack, text: str) -> BusinessRiskFinding:
    return BusinessRiskFinding(
        id=rule.id,
        name=rule.name,
        risk_level=calculate_level_from_score(rule.risk_score),
        risk_score=rule.risk_score,
        evidence=rule.evidence(context, text),
        recommendation=list(rule.recommendation),
    )


def _business_risk_rules() -> List[BusinessRiskRule]:
    return [
        BusinessRiskRule(
            id="missing_acceptance_criteria",
            name="Missing Acceptance Criteria",
            risk_score=6,
            applies=lambda context, text: context.source_type in {"prd", "business_requirement"}
            and not context.acceptance_criteria
            and not _has_any(text, ["acceptance criteria", "given ", "when ", "then ", "must ", "should "]),
            evidence=lambda context, text: ["No explicit acceptance criteria or Given/When/Then checks found."],
            recommendation=[
                "Add measurable acceptance criteria for success, failure, retry, and edge cases.",
                "Turn ambiguous product expectations into testable Given/When/Then examples.",
            ],
        ),
        BusinessRiskRule(
            id="async_callback_gap",
            name="Async Callback / Retry Gap",
            risk_score=10,
            applies=lambda context, text: _has_any(text, ["callback", "webhook", "provider", "async", "delayed"])
            and (
                not _has_all_groups(
                    text,
                    [["timeout", "delay", "delayed"], ["retry", "duplicate", "idempotent", "idempotency"]],
                )
                or _has_unresolved_signal(text, ["timeout", "retry", "duplicate", "idempotent", "idempotency"])
            ),
            evidence=lambda context, text: _evidence_from_keywords(
                text,
                ["callback", "webhook", "provider", "async", "delayed"],
            )
            + [_coverage_gap_evidence(text, "timeout/retry/idempotency behavior")],
            recommendation=[
                "Define timeout, delayed callback, duplicated callback, and callback ordering behavior.",
                "Add idempotency and replay protection checks before release.",
            ],
        ),
        BusinessRiskRule(
            id="payment_reconciliation_gap",
            name="Payment Reconciliation Gap",
            risk_score=11,
            applies=lambda context, text: context.business_domain == "payment"
            and _has_any(text, ["payment", "refund", "ledger", "balance", "settlement", "transaction"])
            and (
                not _has_any(text, ["reconciliation", "settlement", "ledger check", "audit"])
                or _has_unresolved_signal(text, ["reconciliation", "settlement", "ledger", "audit"])
            ),
            evidence=lambda context, text: _evidence_from_keywords(
                text,
                ["payment", "refund", "ledger", "balance", "transaction"],
            )
            + [_coverage_gap_evidence(text, "reconciliation, settlement, or ledger-audit requirement")],
            recommendation=[
                "Add reconciliation checks for provider response drift and long-pending transactions.",
                "Verify ledger balance, transaction record, and user-facing status stay consistent.",
            ],
        ),
        BusinessRiskRule(
            id="state_transition_ambiguity",
            name="State Transition Ambiguity",
            risk_score=8,
            applies=lambda context, text: _has_any(text, ["status", "state", "pending", "completed", "failed"])
            and not _has_state_transition_detail(text),
            evidence=lambda context, text: _evidence_from_keywords(
                text,
                ["status", "state", "pending", "completed", "failed"],
            )
            + ["No explicit state transition or terminal-state rule found."],
            recommendation=[
                "Document allowed state transitions and terminal states.",
                "Add regression cases for invalid transition attempts and out-of-order events.",
            ],
        ),
        BusinessRiskRule(
            id="rollout_observability_gap",
            name="Rollout / Observability Gap",
            risk_score=7,
            applies=lambda context, text: context.source_type in {"prd", "business_requirement", "release_note"}
            and _has_any(text, ["release", "launch", "rollout", "enable", "migration", "new flow"])
            and not _has_any(text, ["rollback", "monitor", "alert", "dashboard", "gray", "canary", "feature flag"]),
            evidence=lambda context, text: _evidence_from_keywords(
                text,
                ["release", "launch", "rollout", "enable", "migration", "new flow"],
            )
            + ["No rollback, monitoring, alerting, or staged rollout plan found."],
            recommendation=[
                "Define rollback trigger, rollback owner, and feature flag strategy.",
                "Add metrics and alerts for failure rate, latency, mismatch rate, and manual intervention volume.",
            ],
        ),
        BusinessRiskRule(
            id="ownership_dependency_gap",
            name="Ownership / Dependency Gap",
            risk_score=5,
            applies=lambda context, text: context.source_type in {"prd", "business_requirement", "release_note"}
            and not context.stakeholders
            and _has_any(text, ["dependency", "provider", "client", "merchant", "partner", "external"]),
            evidence=lambda context, text: ["External dependency mentioned without explicit owners or reviewers."],
            recommendation=[
                "List business owner, technical owner, external dependency owner, and final approver.",
                "Add a sign-off checklist for provider/client compatibility risks.",
            ],
        ),
    ]


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _has_all_groups(text: str, keyword_groups: Iterable[Iterable[str]]) -> bool:
    return all(_has_any(text, group) for group in keyword_groups)


def _evidence_from_keywords(text: str, keywords: Iterable[str]) -> List[str]:
    return [f"matched `{keyword}`" for keyword in keywords if keyword in text]


def _has_state_transition_detail(text: str) -> bool:
    if _has_any(text, ["transition", "state machine", "terminal"]):
        return True
    return bool(re.search(r"\bfrom\s+[a-z0-9_ -]{1,40}\s+to\s+[a-z0-9_ -]{1,40}\b", text))


def _has_unresolved_signal(text: str, keywords: Iterable[str]) -> bool:
    uncertainty_words = [
        "not finalized",
        "not defined",
        "not confirmed",
        "still being discussed",
        "to be confirmed",
        "tbd",
        "open question",
        "will be confirmed",
    ]
    if not _has_any(text, keywords) or not _has_any(text, uncertainty_words):
        return False

    for keyword in keywords:
        pattern = rf"(?:{'|'.join(re.escape(word) for word in uncertainty_words)}).{{0,80}}\b{re.escape(keyword)}\b|\b{re.escape(keyword)}\b.{{0,80}}(?:{'|'.join(re.escape(word) for word in uncertainty_words)})"
        if re.search(pattern, text):
            return True
    return False


def _coverage_gap_evidence(text: str, coverage_name: str) -> str:
    if _has_any(
        text,
        [
            "not finalized",
            "not defined",
            "not confirmed",
            "still being discussed",
            "to be confirmed",
            "tbd",
            "open question",
            "will be confirmed",
        ],
    ):
        return f"{coverage_name} is mentioned but still unresolved."
    return f"Missing complete {coverage_name}."

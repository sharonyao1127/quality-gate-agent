from dataclasses import dataclass, field
import re
from typing import Iterable, List, Optional


SUPPORTED_SOURCE_TYPES = {
    "generic",
    "demo",
    "git_diff",
    "api_change",
    "openapi",
    "prd",
    "business_requirement",
    "release_note",
}

SUPPORTED_BUSINESS_DOMAINS = {
    "generic",
    "payment",
    "ads",
    "logistics",
    "healthcare",
    "edtech",
}


@dataclass(frozen=True)
class ChangeContextPack:
    title: str
    source_type: str
    business_domain: str
    raw_text: str
    changed_components: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    risk_hints: List[str] = field(default_factory=list)

    def to_analysis_text(self) -> str:
        sections = [
            f"Title: {self.title}",
            f"Source Type: {self.source_type}",
            f"Business Domain: {self.business_domain}",
        ]
        sections.append(_format_list("Changed Components", self.changed_components))
        sections.append(_format_list("Stakeholders", self.stakeholders))
        sections.append(_format_list("Acceptance Criteria", self.acceptance_criteria))
        sections.append(_format_list("Risk Hints", self.risk_hints))
        sections.extend(["Raw Context:", self.raw_text])
        return "\n".join(section for section in sections if section).strip()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source_type": self.source_type,
            "business_domain": self.business_domain,
            "changed_components": list(self.changed_components),
            "stakeholders": list(self.stakeholders),
            "acceptance_criteria": list(self.acceptance_criteria),
            "risk_hints": list(self.risk_hints),
        }


def build_context_pack(
    raw_text: str,
    source_type: str = "generic",
    title: Optional[str] = None,
    business_domain: Optional[str] = None,
) -> ChangeContextPack:
    normalized_source_type = _normalize_source_type(source_type)
    extracted_title = title or _extract_title(raw_text)
    extracted_domain = business_domain or _extract_labeled_value(raw_text, ["Business Domain", "Domain"])
    normalized_domain = _normalize_business_domain(extracted_domain or _infer_business_domain(raw_text))

    changed_components = _extract_items(raw_text, ["Changed Components", "Components", "Impacted Components"])
    stakeholders = _extract_items(raw_text, ["Stakeholders", "Owners", "Reviewers"])
    acceptance_criteria = _extract_items(
        raw_text,
        ["Acceptance Criteria", "Definition of Done", "Success Criteria"],
    )
    risk_hints = _extract_items(raw_text, ["Risk Hints", "Known Risks", "Risk Notes"])

    return ChangeContextPack(
        title=extracted_title,
        source_type=normalized_source_type,
        business_domain=normalized_domain,
        raw_text=raw_text,
        changed_components=changed_components,
        stakeholders=stakeholders,
        acceptance_criteria=acceptance_criteria,
        risk_hints=risk_hints,
    )


def _normalize_source_type(source_type: str) -> str:
    normalized = source_type.strip().lower().replace("-", "_")
    return normalized if normalized in SUPPORTED_SOURCE_TYPES else "generic"


def _normalize_business_domain(domain: str) -> str:
    normalized = domain.strip().lower().replace("-", "_")
    return normalized if normalized in SUPPORTED_BUSINESS_DOMAINS else "generic"


def _extract_title(raw_text: str) -> str:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title

        match = re.match(r"^(?:Title|PRD|Requirement)\s*:\s*(.+)$", stripped, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "Untitled Change Context"


def _extract_labeled_value(raw_text: str, labels: Iterable[str]) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"^(?:#+\s*)?(?:{label_pattern})\s*:\s*(.+)$", flags=re.IGNORECASE)

    for line in raw_text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _extract_items(raw_text: str, labels: Iterable[str]) -> List[str]:
    inline_value = _extract_labeled_value(raw_text, labels)
    inline_items = _split_items(inline_value) if inline_value else []
    section_items = _extract_markdown_section_items(raw_text, labels)
    return _dedupe_preserving_order(inline_items + section_items)


def _extract_markdown_section_items(raw_text: str, labels: Iterable[str]) -> List[str]:
    wanted = {label.lower() for label in labels}
    items: List[str] = []
    in_section = False

    for line in raw_text.splitlines():
        stripped = line.strip()
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)

        if heading_match:
            heading = heading_match.group(1).strip().rstrip(":").lower()
            in_section = heading in wanted
            continue

        if not in_section:
            continue

        if not stripped:
            continue
        if stripped.startswith("#"):
            break

        bullet_match = re.match(r"^(?:[-*]|\d+\.)\s+(.+)$", stripped)
        if bullet_match:
            items.append(bullet_match.group(1).strip())

    return items


def _split_items(value: str) -> List[str]:
    return [
        item.strip(" -")
        for item in re.split(r"[,;，；]", value)
        if item.strip(" -")
    ]


def _infer_business_domain(raw_text: str) -> str:
    text = raw_text.lower()
    domain_signals = {
        "payment": ["payment", "refund", "ledger", "balance", "settlement", "reconciliation"],
        "ads": ["ads", "ad platform", "campaign", "creative", "ranking", "retrieval", "bid"],
        "logistics": ["logistics", "shipment", "parcel", "route", "warehouse", "station"],
        "healthcare": ["healthcare", "patient", "diagnosis", "appointment", "medical"],
        "edtech": ["course", "lesson", "student", "teacher", "learning", "education"],
    }

    for domain, signals in domain_signals.items():
        if any(signal in text for signal in signals):
            return domain
    return "generic"


def _dedupe_preserving_order(items: Iterable[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped


def _format_list(title: str, items: List[str]) -> str:
    if not items:
        return ""
    return "\n".join([f"{title}:"] + [f"- {item}" for item in items])

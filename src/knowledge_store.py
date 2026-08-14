from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_DIR = ROOT / "knowledge" / "risk_patterns"


@dataclass(frozen=True)
class RiskKnowledgePattern:
    id: str
    domain: str
    name: str
    signals: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recommended_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "domain": self.domain,
            "name": self.name,
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommended_checks": list(self.recommended_checks),
        }


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    query: str
    domain: str
    matched_patterns: List[RiskKnowledgePattern]

    def to_dict(self) -> Dict[str, object]:
        return {
            "query_hash": hashlib.sha256(self.query.encode("utf-8")).hexdigest()[:16],
            "query_preview": _safe_query_preview(self.query),
            "domain": self.domain,
            "matched_patterns": [pattern.to_dict() for pattern in self.matched_patterns],
        }


def load_risk_patterns(knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR) -> List[RiskKnowledgePattern]:
    patterns: List[RiskKnowledgePattern] = []
    for path in sorted(knowledge_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in data.get("patterns", []):
            patterns.append(
                RiskKnowledgePattern(
                    id=item["id"],
                    domain=item.get("domain", "generic"),
                    name=item["name"],
                    signals=list(item.get("signals", [])),
                    risks=list(item.get("risks", [])),
                    recommended_checks=list(item.get("recommended_checks", [])),
                )
            )
    return patterns


def retrieve_risk_patterns(
    query: str,
    domain: str = "generic",
    patterns: Optional[List[RiskKnowledgePattern]] = None,
    limit: int = 5,
) -> KnowledgeRetrievalResult:
    loaded_patterns = patterns if patterns is not None else load_risk_patterns()
    query_lower = query.lower()
    domain_lower = domain.lower()

    scored = []
    for pattern in loaded_patterns:
        if domain_lower != "generic" and pattern.domain != domain_lower:
            continue
        score = _score_pattern(query_lower, pattern)
        if score > 0:
            scored.append((score, pattern))

    scored.sort(key=lambda item: (-item[0], item[1].id))
    return KnowledgeRetrievalResult(
        query=query,
        domain=domain_lower,
        matched_patterns=[pattern for _, pattern in scored[:limit]],
    )


def generate_knowledge_context(result: KnowledgeRetrievalResult) -> str:
    if not result.matched_patterns:
        return ""

    lines = [
        "Retrieved Risk Knowledge:",
        f"Domain: {result.domain}",
    ]
    for pattern in result.matched_patterns:
        lines.append(f"- {pattern.name} ({pattern.id})")
        if pattern.risks:
            lines.append(f"  Risks: {'; '.join(pattern.risks)}")
        if pattern.recommended_checks:
            lines.append(f"  Recommended checks: {'; '.join(pattern.recommended_checks)}")
    return "\n".join(lines)


def generate_knowledge_report(result: KnowledgeRetrievalResult) -> str:
    lines = [
        "# Risk Knowledge Retrieval",
        "",
        f"- **Domain:** {result.domain}",
        f"- **Matched Patterns:** {len(result.matched_patterns)}",
        "",
        "## Patterns",
        "",
    ]

    if not result.matched_patterns:
        lines.append("- No matched knowledge patterns.")
    else:
        for pattern in result.matched_patterns:
            lines.extend(
                [
                    f"### {pattern.name}",
                    f"- **ID:** `{pattern.id}`",
                    f"- **Signals:** {', '.join(pattern.signals)}",
                    "- **Risks:**",
                ]
            )
            for risk in pattern.risks:
                lines.append(f"  - {risk}")
            lines.append("- **Recommended Checks:**")
            for check in pattern.recommended_checks:
                lines.append(f"  - {check}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _score_pattern(query_lower: str, pattern: RiskKnowledgePattern) -> int:
    score = 0
    for signal in pattern.signals:
        if signal.lower() in query_lower:
            score += 3
    return score


def _safe_query_preview(query: str, max_length: int = 160) -> str:
    metadata = query.split("Raw Context:", maxsplit=1)[0].strip()
    preview_source = metadata or query
    compact = " ".join(preview_source.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length].rstrip()}..."

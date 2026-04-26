from src.gate_analyzer import GateAnalysisResult


def generate_gate_report(result: GateAnalysisResult) -> str:
    lines = [
        "# Quality Gate Report",
        "",
        f"## Overall Risk Level: {result.overall_risk_level.upper()}",
        "",
        f"## Overall Risk Score: {result.overall_risk_score} / 15",
        "",
        "## Matched Risk Rules",
        "",
        "| Rule | Level | Score | Matched Keywords |",
        "|---|---|---:|---|",
    ]

    if not result.matches:
        lines.append("| No matched risk | low | 0 | N/A |")
    else:
        for match in result.matches:
            lines.append(
                f"| {match.name} | {match.risk_level} | {match.risk_score} | {', '.join(match.matched_keywords)} |"
            )

    lines.extend(["", "## Risk Dimensions", ""])

    if result.matches:
        for match in result.matches:
            lines.append(f"### {match.name}")
            for key, value in match.dimensions.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
    else:
        lines.append("- No risk dimensions detected by current rules.")

    lines.extend(["", "## Impacted Areas", ""])

    impacted = []
    for match in result.matches:
        impacted.extend(match.impacted_areas)

    if impacted:
        for area in sorted(set(impacted)):
            lines.append(f"- {area}")
    else:
        lines.append("- No impacted areas detected by current rules.")

    lines.extend(["", "## Suggested Regression Scope", ""])

    regressions = []
    for match in result.matches:
        regressions.extend(match.suggested_regression)

    if regressions:
        for item in sorted(set(regressions)):
            lines.append(f"- {item}")
    else:
        lines.append("- Manual review recommended.")

    lines.extend(["", "## Gate Recommendation", ""])

    if result.overall_risk_level == "high":
        lines.append("High-risk change detected. Regression scope should be reviewed before merge/release.")
    elif result.overall_risk_level == "medium":
        lines.append("Medium-risk change detected. Targeted regression is recommended.")
    else:
        lines.append("Low-risk change detected by current rules. Manual review may still be needed.")

    return "\n".join(lines)

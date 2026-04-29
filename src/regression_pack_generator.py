from src.gate_analyzer import GateAnalysisResult


def generate_regression_pack(result: GateAnalysisResult) -> dict:
    checks = []
    seen_ids = set()

    for match in result.matches:
        for area in match.impacted_areas:
            area_lower = area.lower()

            if "idempotency" in area_lower:
                check = {
                    "id": "duplicate_request_check",
                    "type": "api",
                    "priority": "P0",
                    "reason": "idempotency risk",
                }
            elif "callback" in area_lower or "reconciliation" in area_lower:
                check = {
                    "id": "delayed_callback_check",
                    "type": "integration",
                    "priority": "P0",
                    "reason": "async callback risk",
                }
            elif "status" in area_lower or "frontend/backend" in area_lower:
                check = {
                    "id": "status_display_check",
                    "type": "contract",
                    "priority": "P1",
                    "reason": "user-facing state changed",
                }
            else:
                continue

            if check["id"] not in seen_ids:
                checks.append(check)
                seen_ids.add(check["id"])

    return {
        "risk_level": result.overall_risk_level,
        "required_checks": checks,
    }


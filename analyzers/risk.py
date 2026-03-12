from __future__ import annotations

from typing import Any


def _level(score: int) -> str:
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def assess_risk(file_data: dict[str, Any]) -> tuple[int, str, list[str]]:
    patterns = set(file_data.get("patterns", []))
    category = file_data.get("category", "other")
    status = file_data.get("status", "modified")
    additions = int(file_data.get("additions", 0))
    deletions = int(file_data.get("deletions", 0))

    score = 1
    reasons: list[str] = []

    if "auth_related" in patterns:
        score += 4
        reasons.append("Touches authentication/authorization code")

    if "secret_exposure" in patterns:
        score += 5
        reasons.append("Signal: possible secret/credential exposure")

    if "schema_change" in patterns:
        score += 4
        reasons.append("Modifies schema or migration surface")

    if "config_change" in patterns:
        score += 3
        reasons.append("Changes runtime/build configuration")

    if "signature_change" in patterns:
        score += 2
        reasons.append("Function/method signatures changed")

    if status == "deleted":
        score += 2
        reasons.append("Removes existing file")

    if additions + deletions > 300:
        score += 2
        reasons.append("Large patch size")
    elif additions + deletions > 120:
        score += 1
        reasons.append("Moderate patch size")

    if "behavior_change" in patterns:
        score += 2
        reasons.append("Contains executable behavior changes")

    if category in {"test", "docs"}:
        score -= 1
        reasons.append("Primarily non-production surface")

    plugin_delta = int(file_data.get("plugin_risk_score_delta", 0))
    if plugin_delta > 0:
        score += plugin_delta

    plugin_reasons = file_data.get("plugin_risk_reasons", [])
    if isinstance(plugin_reasons, list):
        for reason in plugin_reasons:
            if isinstance(reason, str) and reason.strip():
                reasons.append(reason.strip())

    score = max(1, min(10, score))
    return score, _level(score), reasons

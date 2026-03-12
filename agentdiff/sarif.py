from __future__ import annotations

from typing import Any

from . import __version__


def _risk_level_to_sarif(risk_level: str) -> str:
    if risk_level == "high":
        return "error"
    if risk_level == "medium":
        return "warning"
    return "note"


def _rule_name(rule_id: str) -> str:
    return rule_id.split("/")[-1].replace("_", " ").title()


def _file_location(path: str) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {
                "uri": path,
                "uriBaseId": "%SRCROOT%",
            }
        }
    }


def analysis_to_sarif(analysis: dict[str, Any]) -> dict[str, Any]:
    files = analysis.get("files", [])
    results: list[dict[str, Any]] = []
    rule_ids: set[str] = set()

    for file_data in files:
        path = str(file_data.get("path", ""))
        if not path:
            continue

        risk_level = str(file_data.get("risk_level", "low"))
        risk_score = int(file_data.get("risk_score", 1))
        reasons = file_data.get("risk_reasons", [])
        message_text = (
            f"Risk={risk_level} (score {risk_score}/10). "
            + ("; ".join(reasons) if reasons else "No explicit reasons provided.")
        )

        risk_rule_id = f"agentdiff/risk/{risk_level}"
        rule_ids.add(risk_rule_id)
        results.append(
            {
                "ruleId": risk_rule_id,
                "level": _risk_level_to_sarif(risk_level),
                "message": {"text": message_text},
                "locations": [{"physicalLocation": _file_location(path)["physicalLocation"]}],
                "properties": {
                    "agentdiff.risk_score": risk_score,
                    "agentdiff.change_type": file_data.get("change_type", "modified"),
                },
            }
        )

        pattern_confidence = file_data.get("pattern_confidence", {})
        if isinstance(pattern_confidence, dict):
            for pattern in sorted(pattern_confidence):
                confidence = float(pattern_confidence.get(pattern, 0.0))
                pattern_rule = f"agentdiff/pattern/{pattern}"
                rule_ids.add(pattern_rule)
                results.append(
                    {
                        "ruleId": pattern_rule,
                        "level": "warning" if confidence >= 0.75 else "note",
                        "message": {"text": f"Detected pattern `{pattern}` with confidence {confidence:.2f}."},
                        "locations": [{"physicalLocation": _file_location(path)["physicalLocation"]}],
                        "properties": {
                            "agentdiff.confidence": round(confidence, 2),
                            "agentdiff.category": file_data.get("category", "other"),
                        },
                    }
                )

    rules = [
        {
            "id": rule_id,
            "name": _rule_name(rule_id),
            "shortDescription": {"text": _rule_name(rule_id)},
            "properties": {"tags": ["agentdiff", "code-review"]},
        }
        for rule_id in sorted(rule_ids)
    ]

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AgentDiff",
                        "version": __version__,
                        "informationUri": "https://github.com/natiixnt/AgentDiff",
                        "rules": rules,
                    }
                },
                "originalUriBaseIds": {
                    "%SRCROOT%": {
                        "uri": "file:///"
                    }
                },
                "results": results,
            }
        ],
    }

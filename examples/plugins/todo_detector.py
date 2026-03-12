from __future__ import annotations

from typing import Any


def analyze_file(file_data: dict[str, Any]) -> dict[str, Any]:
    patch = str(file_data.get("patch", ""))
    todo_hits = []
    for line in patch.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        lowered = line.lower()
        if "todo" in lowered or "fixme" in lowered:
            todo_hits.append(line)

    if not todo_hits:
        return {}

    return {
        "patterns": [
            {
                "name": "todo_marker",
                "confidence": 0.72,
            }
        ],
        "risk_reasons": [
            f"Plugin(todo_detector): TODO/FIXME introduced ({len(todo_hits)} added lines)",
        ],
        "risk_score_delta": 1,
    }

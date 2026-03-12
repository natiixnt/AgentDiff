from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any


def _group_key(file_data: dict[str, Any]) -> tuple[str, str]:
    patterns = set(file_data.get("patterns", []))
    category = file_data.get("category", "other")
    path = file_data.get("path", "")

    if "auth_related" in patterns or category == "auth":
        return "auth", "Auth & Access Control"

    if "schema_change" in patterns or category == "schema":
        return "schema", "Schema & Data Contract"

    if "config_change" in patterns or category == "config":
        return "config", "Configuration & Runtime"

    if category == "test":
        return "tests", "Tests"

    if category == "docs":
        return "docs", "Documentation"

    parts = [part for part in PurePosixPath(path).parts if part not in {".", ""}]
    if not parts:
        return "misc", "Miscellaneous"

    if len(parts) >= 2:
        key = f"component:{parts[0]}/{parts[1]}"
        title = f"Component: {parts[0]}/{parts[1]}"
        return key, title

    key = f"component:{parts[0]}"
    title = f"Component: {parts[0]}"
    return key, title


def build_change_groups(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for file_data in files:
        key, title = _group_key(file_data)
        if key not in grouped:
            grouped[key] = {
                "id": key,
                "title": title,
                "files": [],
                "risk": "low",
                "risk_score": 0,
                "change_types": defaultdict(int),
            }

        group = grouped[key]
        group["files"].append(file_data["path"])
        group["change_types"][file_data.get("change_type", "modified")] += 1

        score = int(file_data.get("risk_score", 1))
        if score > group["risk_score"]:
            group["risk_score"] = score
            group["risk"] = file_data.get("risk_level", "low")

    groups = list(grouped.values())
    for group in groups:
        group["change_types"] = dict(group["change_types"])
        group["files"] = sorted(set(group["files"]))

    groups.sort(key=lambda g: (-g["risk_score"], -len(g["files"]), g["title"]))
    return groups


def suggest_review_order(
    files: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    plan_data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    file_by_path = {file_data["path"]: file_data for file_data in files}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    steps = []
    if isinstance(plan_data, dict):
        raw_steps = plan_data.get("steps", [])
        if isinstance(raw_steps, list):
            steps = [step for step in raw_steps if isinstance(step, dict)]

    for step in steps:
        step_files = step.get("files", [])
        if not isinstance(step_files, list):
            continue

        for path in step_files:
            if path in file_by_path and path not in seen:
                file_data = file_by_path[path]
                result.append(
                    {
                        "path": path,
                        "reason": f"Planned step: {step.get('name', 'unnamed step')}",
                        "risk": file_data.get("risk_level", "low"),
                        "risk_score": file_data.get("risk_score", 1),
                    }
                )
                seen.add(path)

    group_order: dict[str, int] = {group["id"]: index for index, group in enumerate(groups)}
    fallback_sorted = sorted(
        files,
        key=lambda f: (
            -int(f.get("risk_score", 1)),
            group_order.get(f.get("group_id", ""), 999),
            f.get("path", ""),
        ),
    )

    for file_data in fallback_sorted:
        path = file_data["path"]
        if path in seen:
            continue
        reason = "High-risk surface" if file_data.get("risk_level") == "high" else "Group context"
        result.append(
            {
                "path": path,
                "reason": reason,
                "risk": file_data.get("risk_level", "low"),
                "risk_score": file_data.get("risk_score", 1),
            }
        )
        seen.add(path)

    return result

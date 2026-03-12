from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath
from typing import Any

from analyzers import (
    assess_risk,
    build_change_groups,
    build_related_files,
    categorize_file,
    detect_pattern_confidence,
    infer_ast_change_type,
    infer_change_type,
    suggest_review_order,
)

from .diff_parser import parse_git_diff
from .ignore import should_ignore_change
from .models import FileChange
from .plugins import LoadedPlugin


def _change_facets(change_type: str, patterns: set[str]) -> list[str]:
    facets: list[str] = []
    for value in ("rename", "refactor", "extraction", "behavior_change"):
        if value == change_type or value in patterns:
            facets.append(value)
    if not facets:
        facets.append(change_type)
    return facets


def _augment_extractions(files: list[dict[str, Any]]) -> None:
    added_files = [f for f in files if f.get("status") == "added" and f.get("additions", 0) >= 25]
    modified_files = [f for f in files if f.get("status") == "modified" and f.get("deletions", 0) >= 20]

    for added in added_files:
        added_path = PurePosixPath(added["path"])
        for modified in modified_files:
            mod_path = PurePosixPath(modified["path"])
            if added_path.parent != mod_path.parent:
                continue

            added_name = added_path.stem.lower()
            if added_name in modified.get("patch", "").lower():
                added.setdefault("patterns", []).append("extraction")
                modified.setdefault("patterns", []).append("extraction")
                added.setdefault("pattern_confidence", {})
                modified.setdefault("pattern_confidence", {})
                added["pattern_confidence"]["extraction"] = max(
                    float(added["pattern_confidence"].get("extraction", 0.0)), 0.73
                )
                modified["pattern_confidence"]["extraction"] = max(
                    float(modified["pattern_confidence"].get("extraction", 0.0)), 0.7
                )
                if added.get("change_type") == "behavior_change":
                    added["change_type"] = "extraction"
                if modified.get("change_type") == "behavior_change":
                    modified["change_type"] = "refactor"


def _file_record(change: FileChange, secret_ignore_patterns: list[str] | None = None) -> dict[str, Any]:
    path = change.path
    category = categorize_file(path)
    pattern_confidence = detect_pattern_confidence(
        change, category, secret_ignore_patterns=secret_ignore_patterns
    )
    pattern_set = set(pattern_confidence.keys())
    patterns = sorted(pattern_set)
    ast_hint = infer_ast_change_type(change, pattern_set)
    change_type = ast_hint or infer_change_type(change, pattern_set)

    record: dict[str, Any] = {
        "path": path,
        "old_path": change.old_path,
        "new_path": change.new_path,
        "status": change.status,
        "category": category,
        "patterns": patterns,
        "pattern_confidence": {key: pattern_confidence[key] for key in sorted(pattern_confidence)},
        "change_type": change_type,
        "change_facets": _change_facets(change_type, pattern_set),
        "additions": len(change.added_lines),
        "deletions": len(change.removed_lines),
        "patch": change.raw_patch,
        "metadata": change.metadata,
    }
    return record


def _summary(files: list[dict[str, Any]], groups: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts = Counter(file_data["category"] for file_data in files)
    change_type_counts = Counter(file_data["change_type"] for file_data in files)
    risk_counts = Counter(file_data["risk_level"] for file_data in files)

    return {
        "total_files": len(files),
        "total_groups": len(groups),
        "total_additions": sum(int(file_data.get("additions", 0)) for file_data in files),
        "total_deletions": sum(int(file_data.get("deletions", 0)) for file_data in files),
        "categories": dict(category_counts),
        "change_types": dict(change_type_counts),
        "risk_levels": dict(risk_counts),
    }


def _apply_plugins(files: list[dict[str, Any]], plugins: list[LoadedPlugin]) -> None:
    if not plugins:
        return

    for file_data in files:
        file_data.setdefault("patterns", [])
        file_data.setdefault("pattern_confidence", {})
        file_data.setdefault("plugin_risk_reasons", [])
        file_data.setdefault("plugin_risk_score_delta", 0)

        for plugin in plugins:
            try:
                output = plugin.analyze_file(dict(file_data))
            except Exception as exc:
                file_data["plugin_risk_reasons"].append(f"Plugin `{plugin.name}` failed: {exc}")
                continue

            if not isinstance(output, dict):
                continue

            raw_patterns = output.get("patterns", [])
            if isinstance(raw_patterns, list):
                for item in raw_patterns:
                    if isinstance(item, str):
                        pattern_name = item
                        confidence = 0.6
                    elif isinstance(item, dict):
                        pattern_name = str(item.get("name", "")).strip()
                        confidence = float(item.get("confidence", 0.6))
                    else:
                        continue

                    if not pattern_name:
                        continue

                    file_data["patterns"].append(pattern_name)
                    current = float(file_data["pattern_confidence"].get(pattern_name, 0.0))
                    file_data["pattern_confidence"][pattern_name] = round(max(current, confidence), 2)

            raw_reasons = output.get("risk_reasons", [])
            if isinstance(raw_reasons, list):
                for reason in raw_reasons:
                    if isinstance(reason, str) and reason.strip():
                        file_data["plugin_risk_reasons"].append(reason.strip())

            delta = output.get("risk_score_delta", 0)
            if isinstance(delta, (int, float)) and delta > 0:
                file_data["plugin_risk_score_delta"] = int(file_data["plugin_risk_score_delta"]) + int(delta)


def _collect_plan_files(plan_data: dict[str, Any] | None) -> list[str]:
    if not isinstance(plan_data, dict):
        return []
    raw_steps = plan_data.get("steps", [])
    if not isinstance(raw_steps, list):
        return []

    seen: set[str] = set()
    ordered: list[str] = []
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        raw_files = step.get("files", [])
        if not isinstance(raw_files, list):
            continue
        for path in raw_files:
            if not isinstance(path, str):
                continue
            candidate = path.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _plan_drift(files: list[dict[str, Any]], plan_data: dict[str, Any] | None) -> dict[str, Any]:
    planned_ordered = _collect_plan_files(plan_data)
    if not planned_ordered:
        return {
            "has_plan": False,
            "planned_files": [],
            "planned_but_unchanged": [],
            "changed_but_unplanned": [],
            "planned_but_unchanged_count": 0,
            "changed_but_unplanned_count": 0,
        }

    changed_paths = {file_data["path"] for file_data in files}
    planned_set = set(planned_ordered)

    planned_but_unchanged = [path for path in planned_ordered if path not in changed_paths]
    changed_but_unplanned = sorted(path for path in changed_paths if path not in planned_set)

    return {
        "has_plan": True,
        "planned_files": planned_ordered,
        "planned_but_unchanged": planned_but_unchanged,
        "changed_but_unplanned": changed_but_unplanned,
        "planned_but_unchanged_count": len(planned_but_unchanged),
        "changed_but_unplanned_count": len(changed_but_unplanned),
    }


def analyze_diff(
    diff_text: str,
    plan_data: dict[str, Any] | None = None,
    ignore_patterns: list[str] | None = None,
    secret_ignore_patterns: list[str] | None = None,
    plugins: list[LoadedPlugin] | None = None,
) -> dict[str, Any]:
    parsed = parse_git_diff(diff_text)
    ignored_patterns = list(ignore_patterns or [])
    ignored_files: list[str] = []

    if ignored_patterns:
        filtered: list[FileChange] = []
        for change in parsed:
            if should_ignore_change(change, ignored_patterns):
                ignored_files.append(change.path)
                continue
            filtered.append(change)
        parsed = filtered

    files = [_file_record(change, secret_ignore_patterns=secret_ignore_patterns) for change in parsed]

    _augment_extractions(files)
    _apply_plugins(files, plugins or [])

    for file_data in files:
        # Keep pattern list stable and unique in final output.
        file_data["patterns"] = sorted(set(file_data.get("patterns", [])))
        pattern_confidence = {
            key: round(float(value), 2) for key, value in file_data.get("pattern_confidence", {}).items()
        }
        for pattern in file_data["patterns"]:
            pattern_confidence.setdefault(pattern, 0.6)
        file_data["pattern_confidence"] = {
            key: pattern_confidence[key] for key in sorted(pattern_confidence)
        }
        file_data["change_facets"] = _change_facets(
            file_data.get("change_type", "modified"), set(file_data["patterns"])
        )
        risk_score, risk_level, risk_reasons = assess_risk(file_data)
        file_data["risk_score"] = risk_score
        file_data["risk_level"] = risk_level
        file_data["risk_reasons"] = risk_reasons

    groups = build_change_groups(files)
    group_by_path: dict[str, str] = {}
    for group in groups:
        for path in group["files"]:
            group_by_path[path] = group["id"]

    for file_data in files:
        file_data["group_id"] = group_by_path.get(file_data["path"], "misc")

    related_map = build_related_files(files)
    for file_data in files:
        file_data["related_files"] = related_map.get(file_data["path"], [])

    review_order = suggest_review_order(files, groups, plan_data)
    plan_drift = _plan_drift(files, plan_data)

    return {
        "summary": _summary(files, groups),
        "groups": groups,
        "files": sorted(files, key=lambda item: (-item["risk_score"], item["path"])),
        "review_order": review_order,
        "plan_drift": plan_drift,
        "ignored": {
            "patterns": ignored_patterns,
            "files": sorted(set(ignored_files)),
            "count": len(set(ignored_files)),
        },
        "plan": plan_data or {},
    }

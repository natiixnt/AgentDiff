from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Iterable

from agentdiff.models import FileChange

SIGNATURE_PATTERNS = [
    re.compile(r"^\s*def\s+\w+\s*\("),
    re.compile(r"^\s*async\s+def\s+\w+\s*\("),
    re.compile(r"^\s*function\s+\w+\s*\("),
    re.compile(r"^\s*(?:public|private|protected)?\s*\w+[\<\>\w\[\],\s]*\s+\w+\s*\("),
    re.compile(r"^\s*export\s+(?:async\s+)?function\s+\w+\s*\("),
    re.compile(r"^\s*const\s+\w+\s*=\s*\([^)]*\)\s*=>"),
]

SCHEMA_LINE_PATTERNS = [
    re.compile(r"\b(create|alter|drop)\s+table\b", re.IGNORECASE),
    re.compile(r"\b(add|drop)\s+column\b", re.IGNORECASE),
    re.compile(r"\bprisma\b", re.IGNORECASE),
]

AUTH_LINE_PATTERNS = [
    re.compile(r"\b(auth|authorize|authentication|jwt|token|oauth|permission|rbac)\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
]

CONFIG_LINE_PATTERNS = [
    re.compile(r"\b(feature_flag|timeout|retries|base_url|endpoint)\b", re.IGNORECASE),
    re.compile(r"\b(env|config|setting)\b", re.IGNORECASE),
]

CODE_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".go",
    ".rb",
    ".rs",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".swift",
    ".kt",
}


def _matches_any(line: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(line) for pattern in patterns)


def _match_count(lines: list[str], patterns: Iterable[re.Pattern[str]]) -> int:
    return sum(1 for line in lines if _matches_any(line, patterns))


def _is_code_file(path: str) -> bool:
    return PurePosixPath(path or "").suffix.lower() in CODE_EXTS


def _is_probably_behavior_change(change: FileChange) -> bool:
    # Ignore whitespace-only churn to avoid false positives.
    added = [line for line in change.added_lines if line.strip()]
    removed = [line for line in change.removed_lines if line.strip()]
    if not added and not removed:
        return False
    if not _is_code_file(change.path):
        return False
    return True


def _has_signature_change(change: FileChange) -> bool:
    if not _is_code_file(change.path):
        return False
    added_signature = any(_matches_any(line, SIGNATURE_PATTERNS) for line in change.added_lines)
    removed_signature = any(_matches_any(line, SIGNATURE_PATTERNS) for line in change.removed_lines)
    return added_signature or removed_signature


def _is_config_change(change: FileChange, category: str) -> bool:
    if category == "config":
        return True
    path = (change.path or "").lower()
    if "/.github/workflows/" in f"/{path}":
        return True
    combined = change.added_lines + change.removed_lines
    return any(_matches_any(line, CONFIG_LINE_PATTERNS) for line in combined)


def _is_schema_change(change: FileChange, category: str) -> bool:
    if category == "schema":
        return True
    combined = change.added_lines + change.removed_lines
    return any(_matches_any(line, SCHEMA_LINE_PATTERNS) for line in combined)


def _is_auth_change(change: FileChange, category: str) -> bool:
    if category == "auth":
        return True
    combined = change.added_lines + change.removed_lines
    return any(_matches_any(line, AUTH_LINE_PATTERNS) for line in combined)


def detect_pattern_confidence(change: FileChange, category: str) -> dict[str, float]:
    confidence: dict[str, float] = {}
    combined = change.added_lines + change.removed_lines

    if change.status == "renamed":
        similarity = str(change.metadata.get("similarity_index", "")).replace("%", "").strip()
        try:
            score = int(similarity)
            if score >= 90:
                confidence["rename"] = 0.98
            elif score >= 75:
                confidence["rename"] = 0.9
            else:
                confidence["rename"] = 0.78
        except ValueError:
            confidence["rename"] = 0.82

    if _has_signature_change(change):
        signature_hits = _match_count(change.added_lines + change.removed_lines, SIGNATURE_PATTERNS)
        confidence["signature_change"] = min(0.98, 0.68 + (signature_hits * 0.08))

    if _is_config_change(change, category):
        if category == "config":
            confidence["config_change"] = 0.96
        else:
            config_hits = _match_count(combined, CONFIG_LINE_PATTERNS)
            confidence["config_change"] = min(0.9, 0.62 + (config_hits * 0.08))

    if _is_schema_change(change, category):
        if category == "schema":
            confidence["schema_change"] = 0.95
        else:
            schema_hits = _match_count(combined, SCHEMA_LINE_PATTERNS)
            confidence["schema_change"] = min(0.92, 0.66 + (schema_hits * 0.1))

    if _is_auth_change(change, category):
        if category == "auth":
            confidence["auth_related"] = 0.95
        else:
            auth_hits = _match_count(combined, AUTH_LINE_PATTERNS)
            confidence["auth_related"] = min(0.92, 0.64 + (auth_hits * 0.08))

    if _is_probably_behavior_change(change):
        churn = len([line for line in combined if line.strip()])
        confidence["behavior_change"] = min(0.9, 0.56 + (churn / 240))

    # Clamp and round to keep payload stable and readable.
    return {pattern: round(max(0.0, min(1.0, value)), 2) for pattern, value in confidence.items()}


def detect_patterns(change: FileChange, category: str) -> set[str]:
    return set(detect_pattern_confidence(change, category).keys())


def infer_change_type(change: FileChange, patterns: set[str]) -> str:
    if "rename" in patterns and "behavior_change" not in patterns:
        return "rename"

    if "rename" in patterns and "behavior_change" in patterns:
        return "refactor"

    if "extraction" in patterns:
        return "extraction"

    if change.status == "added" and len(change.added_lines) >= 30:
        return "extraction"

    if "signature_change" in patterns and "behavior_change" not in patterns:
        return "refactor"

    if "signature_change" in patterns and "behavior_change" in patterns:
        return "behavior_change"

    if "behavior_change" in patterns and abs(len(change.added_lines) - len(change.removed_lines)) <= 12:
        return "refactor"

    if "behavior_change" in patterns:
        return "behavior_change"

    if "config_change" in patterns:
        return "config_change"

    return change.status

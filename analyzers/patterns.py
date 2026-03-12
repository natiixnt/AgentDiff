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


def detect_patterns(change: FileChange, category: str) -> set[str]:
    patterns: set[str] = set()

    if change.status == "renamed":
        patterns.add("rename")

    if _has_signature_change(change):
        patterns.add("signature_change")

    if _is_config_change(change, category):
        patterns.add("config_change")

    if _is_schema_change(change, category):
        patterns.add("schema_change")

    if _is_auth_change(change, category):
        patterns.add("auth_related")

    if _is_probably_behavior_change(change):
        patterns.add("behavior_change")

    return patterns


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

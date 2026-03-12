from __future__ import annotations

import re
from pathlib import Path


def read_secret_ignore_patterns(path: str | None = None) -> list[str]:
    """Load ignore patterns for secret detection.

    Lines support:
    - plain substring match (case-insensitive)
    - regex with `re:` prefix
    """
    ignore_path = Path(path) if path else Path(".agentdiff-secrets-ignore")
    if not ignore_path.exists():
        return []

    patterns: list[str] = []
    for raw_line in ignore_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def secret_line_is_ignored(line: str, patterns: list[str]) -> bool:
    lowered = line.lower()
    for pattern in patterns:
        if pattern.startswith("re:"):
            expr = pattern[3:]
            try:
                if re.search(expr, line):
                    return True
            except re.error:
                # Invalid regex acts as plain substring to avoid hard-failing analysis.
                if expr.lower() and expr.lower() in lowered:
                    return True
            continue

        if pattern.lower() in lowered:
            return True
    return False

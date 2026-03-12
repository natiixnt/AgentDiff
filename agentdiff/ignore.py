from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from .models import FileChange


def read_ignore_patterns(path: str | None = None) -> list[str]:
    """Load ignore patterns from .agentdiffignore-style file."""
    ignore_path = Path(path) if path else Path(".agentdiffignore")
    if not ignore_path.exists():
        return []

    patterns: list[str] = []
    for raw_line in ignore_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _candidate_paths(path: str) -> list[str]:
    candidates = [path]
    if path.startswith("./"):
        candidates.append(path[2:])
    else:
        candidates.append(f"./{path}")
    return candidates


def should_ignore_path(path: str, patterns: list[str]) -> bool:
    if not path:
        return False

    for candidate in _candidate_paths(path):
        for pattern in patterns:
            if fnmatch(candidate, pattern):
                return True
            if pattern.endswith("/") and candidate.startswith(pattern):
                return True
            if fnmatch(f"/{candidate}", pattern):
                return True
            if fnmatch(candidate, f"**/{pattern}"):
                return True
    return False


def should_ignore_change(change: FileChange, patterns: list[str]) -> bool:
    paths = {change.path, change.old_path, change.new_path}
    return any(should_ignore_path(path, patterns) for path in paths if path)

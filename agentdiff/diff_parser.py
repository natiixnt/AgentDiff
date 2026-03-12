from __future__ import annotations

from typing import Iterable

from .models import FileChange


def _strip_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _parse_header_paths(line: str) -> tuple[str, str]:
    # Example: diff --git a/src/a.py b/src/a.py
    parts = line.strip().split()
    if len(parts) < 4:
        return "", ""
    old_path = _strip_prefix(parts[2])
    new_path = _strip_prefix(parts[3])
    return old_path, new_path


def _finalize_change(change: FileChange | None, changes: list[FileChange]) -> None:
    if change is None:
        return

    if change.old_path == "/dev/null":
        change.status = "added"
        change.old_path = ""
    if change.new_path == "/dev/null":
        change.status = "deleted"
        change.new_path = ""

    changes.append(change)


def parse_git_diff(diff_text: str) -> list[FileChange]:
    """Parse unified git diff output into file-level changes."""
    changes: list[FileChange] = []
    current: FileChange | None = None
    patch_lines: list[str] = []

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current is not None:
                current.raw_patch = "".join(patch_lines)
                _finalize_change(current, changes)

            old_path, new_path = _parse_header_paths(line)
            current = FileChange(
                old_path=old_path,
                new_path=new_path,
                status="modified",
                raw_patch="",
            )
            patch_lines = [line]
            continue

        if current is None:
            continue

        patch_lines.append(line)
        stripped = line.rstrip("\n")

        if stripped.startswith("rename from "):
            current.old_path = stripped.removeprefix("rename from ").strip()
            current.status = "renamed"
        elif stripped.startswith("rename to "):
            current.new_path = stripped.removeprefix("rename to ").strip()
            current.status = "renamed"
        elif stripped.startswith("new file mode"):
            current.status = "added"
        elif stripped.startswith("deleted file mode"):
            current.status = "deleted"
        elif stripped.startswith("similarity index"):
            current.metadata["similarity_index"] = stripped.removeprefix(
                "similarity index"
            ).strip()
        elif stripped.startswith("index "):
            current.metadata["index"] = stripped.removeprefix("index ").strip()
        elif stripped.startswith("--- "):
            path = stripped.removeprefix("--- ").strip()
            current.old_path = _strip_prefix(path)
        elif stripped.startswith("+++ "):
            path = stripped.removeprefix("+++ ").strip()
            current.new_path = _strip_prefix(path)
        elif stripped.startswith("+") and not stripped.startswith("+++"):
            current.added_lines.append(stripped[1:])
        elif stripped.startswith("-") and not stripped.startswith("---"):
            current.removed_lines.append(stripped[1:])

    if current is not None:
        current.raw_patch = "".join(patch_lines)
        _finalize_change(current, changes)

    return changes


def join_diff_chunks(changes: Iterable[FileChange]) -> str:
    return "".join(change.raw_patch for change in changes)

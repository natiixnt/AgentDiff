from __future__ import annotations

import ast
from pathlib import PurePosixPath

from agentdiff.models import FileChange

PYTHON_EXTS = {".py"}


def _is_python_file(path: str) -> bool:
    return PurePosixPath(path or "").suffix.lower() in PYTHON_EXTS


def _to_stub_signature(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if not (stripped.startswith("def ") or stripped.startswith("async def ")):
        return None

    candidate = stripped.split("#", 1)[0].rstrip()
    if not candidate:
        return None
    if not candidate.endswith(":"):
        candidate += ":"
    return candidate


def _signature_key(line: str) -> tuple[str, int, int, bool, bool, int] | None:
    stub = _to_stub_signature(line)
    if stub is None:
        return None

    module_source = f"{stub}\n    pass\n"
    try:
        parsed = ast.parse(module_source)
    except SyntaxError:
        return None

    if not parsed.body:
        return None

    node = parsed.body[0]
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None

    args = node.args
    positional_count = len(args.posonlyargs) + len(args.args)
    kwonly_count = len(args.kwonlyargs)
    has_vararg = args.vararg is not None
    has_kwarg = args.kwarg is not None

    default_count = len(args.defaults)
    default_count += len([value for value in args.kw_defaults if value is not None])

    return (node.name, positional_count, kwonly_count, has_vararg, has_kwarg, default_count)


def _extract_signature_keys(lines: list[str]) -> tuple[set[tuple[str, int, int, bool, bool, int]], bool]:
    keys: set[tuple[str, int, int, bool, bool, int]] = set()
    parse_error = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("def ") and not stripped.startswith("async def "):
            continue
        key = _signature_key(line)
        if key is None:
            parse_error = True
            continue
        keys.add(key)

    return keys, parse_error


def infer_ast_change_type(change: FileChange, patterns: set[str]) -> str | None:
    """Infer refined change type using Python AST parsing where possible.

    Returns None when heuristic cannot infer a stronger classification.
    """
    if change.status != "renamed":
        return None

    if not _is_python_file(change.path):
        return None

    added_keys, added_error = _extract_signature_keys(change.added_lines)
    removed_keys, removed_error = _extract_signature_keys(change.removed_lines)

    # Explicit fallback when parse fails and no useful AST evidence exists.
    if (added_error or removed_error) and not added_keys and not removed_keys:
        return None

    churn = len(change.added_lines) + len(change.removed_lines)

    if added_keys and removed_keys:
        added_names = {item[0] for item in added_keys}
        removed_names = {item[0] for item in removed_keys}

        if added_keys == removed_keys and churn <= 24:
            return "rename"

        if added_names == removed_names:
            return "behavior_change"

        overlap = len(added_names & removed_names)
        baseline = max(1, len(added_names | removed_names))
        if (overlap / baseline) >= 0.6:
            return "refactor"

    if "behavior_change" not in patterns and churn <= 8:
        return "rename"

    return None

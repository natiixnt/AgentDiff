from __future__ import annotations

from pathlib import PurePosixPath

CONFIG_FILENAMES = {
    "dockerfile",
    "makefile",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}

CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".lock"}
DOC_EXTS = {".md", ".rst", ".txt", ".adoc"}
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
    ".sql",
}


def categorize_file(path: str) -> str:
    normalized = (path or "").lower()
    p = PurePosixPath(normalized)
    name = p.name

    if not normalized:
        return "other"

    if any("test" in part for part in p.parts) or name.endswith("_test.py") or name.endswith(".spec.ts"):
        return "test"

    if any(part in {"docs", "doc"} for part in p.parts) or p.suffix in DOC_EXTS:
        return "docs"

    if any(term in normalized for term in ("migration", "migrations", "schema", "prisma")):
        return "schema"

    if any(term in normalized for term in ("auth", "oauth", "login", "token", "jwt", "rbac", "permission")):
        return "auth"

    if name in CONFIG_FILENAMES or p.suffix in CONFIG_EXTS:
        return "config"

    if p.suffix in CODE_EXTS:
        return "source"

    return "other"

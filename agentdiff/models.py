from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileChange:
    old_path: str
    new_path: str
    status: str
    raw_patch: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return self.new_path or self.old_path


@dataclass
class AnalysisPlan:
    raw: dict[str, Any]

    @property
    def steps(self) -> list[dict[str, Any]]:
        steps = self.raw.get("steps", [])
        return steps if isinstance(steps, list) else []

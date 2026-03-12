from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any


def _stem(path: str) -> str:
    p = PurePosixPath(path)
    return p.stem.replace("_test", "").replace(".spec", "")


def build_related_files(files: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_dir: dict[str, list[str]] = defaultdict(list)
    by_stem: dict[str, list[str]] = defaultdict(list)

    for file_data in files:
        path = file_data["path"]
        p = PurePosixPath(path)
        by_dir[str(p.parent)].append(path)
        by_stem[_stem(path).lower()].append(path)

    related: dict[str, list[str]] = {}
    for file_data in files:
        path = file_data["path"]
        p = PurePosixPath(path)

        neighbors: set[str] = set()
        neighbors.update(by_dir.get(str(p.parent), []))
        neighbors.update(by_stem.get(_stem(path).lower(), []))

        # Common source/test pairing.
        if "test" in p.name.lower():
            for candidate in by_stem.get(_stem(path).lower(), []):
                neighbors.add(candidate)
        else:
            test_like = {f"test_{p.name}", f"{p.stem}_test{p.suffix}", f"{p.stem}.spec{p.suffix}"}
            for candidate in by_dir.get(str(p.parent), []):
                cp = PurePosixPath(candidate)
                if cp.name in test_like or "test" in candidate.lower():
                    neighbors.add(candidate)

        neighbors.discard(path)
        related[path] = sorted(neighbors)[:6]

    return related

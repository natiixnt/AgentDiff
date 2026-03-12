import unittest

from analyzers.grouping import build_change_groups


def _file(path: str, risk: int = 2) -> dict[str, object]:
    return {
        "path": path,
        "category": "source",
        "patterns": [],
        "change_type": "modified",
        "risk_score": risk,
        "risk_level": "medium" if risk >= 4 else "low",
    }


class GroupingTests(unittest.TestCase):
    def test_monorepo_workspace_grouping_uses_workspace_boundaries(self) -> None:
        files = [
            _file("packages/api/package.json"),
            _file("packages/api/src/auth/service.ts", risk=5),
            _file("packages/api/src/auth/model.ts", risk=4),
            _file("packages/web/package.json"),
            _file("packages/web/src/ui/app.tsx", risk=3),
        ]

        groups = build_change_groups(files)
        titles = {group["title"] for group in groups}

        self.assertIn("Workspace: packages/api / src/auth", titles)
        self.assertIn("Workspace: packages/web / src/ui", titles)

    def test_grouping_falls_back_without_workspace_hints(self) -> None:
        files = [
            _file("src/core/logic.py"),
            _file("src/core/helpers.py"),
            _file("src/http/routes.py"),
        ]

        groups = build_change_groups(files)
        ids = {group["id"] for group in groups}

        self.assertIn("component:src/core", ids)
        self.assertIn("component:src/http", ids)


if __name__ == "__main__":
    unittest.main()

import unittest

from analyzers.ast_heuristics import infer_ast_change_type
from agentdiff.models import FileChange


class AstHeuristicTests(unittest.TestCase):
    def test_python_rename_with_same_signatures_prefers_rename(self) -> None:
        change = FileChange(
            old_path="src/old/worker.py",
            new_path="src/new/worker.py",
            status="renamed",
            raw_patch="",
            added_lines=[
                "def run(task, retries=1):",
                "    return task",
            ],
            removed_lines=[
                "def run(task, retries=1):",
                "    return task",
            ],
        )

        inferred = infer_ast_change_type(change, {"rename", "behavior_change", "signature_change"})
        self.assertEqual(inferred, "rename")

    def test_python_rename_with_signature_shift_marks_behavior_change(self) -> None:
        change = FileChange(
            old_path="src/old/worker.py",
            new_path="src/new/worker.py",
            status="renamed",
            raw_patch="",
            added_lines=["def run(task, retries=1, timeout=5):"],
            removed_lines=["def run(task, retries=1):"],
        )

        inferred = infer_ast_change_type(change, {"rename", "behavior_change", "signature_change"})
        self.assertEqual(inferred, "behavior_change")

    def test_fallback_when_ast_parse_fails(self) -> None:
        change = FileChange(
            old_path="src/old/worker.py",
            new_path="src/new/worker.py",
            status="renamed",
            raw_patch="",
            added_lines=["def run(task, :"],
            removed_lines=["def run(task, :"],
        )

        inferred = infer_ast_change_type(change, {"rename", "signature_change"})
        self.assertIsNone(inferred)


if __name__ == "__main__":
    unittest.main()

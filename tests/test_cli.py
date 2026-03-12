import unittest

from agentdiff.cli import _build_git_diff_command


class CliTests(unittest.TestCase):
    def test_default_git_diff_command(self) -> None:
        cmd = _build_git_diff_command(None, None, None)
        self.assertEqual(cmd, ["git", "diff", "--find-renames"])

    def test_git_diff_with_range(self) -> None:
        cmd = _build_git_diff_command("main..HEAD", None, None)
        self.assertEqual(cmd, ["git", "diff", "--find-renames", "main..HEAD"])

    def test_git_diff_with_from_to(self) -> None:
        cmd = _build_git_diff_command(None, "main", "feature")
        self.assertEqual(cmd, ["git", "diff", "--find-renames", "main..feature"])

    def test_git_diff_with_from_only(self) -> None:
        cmd = _build_git_diff_command(None, "main", None)
        self.assertEqual(cmd, ["git", "diff", "--find-renames", "main"])

    def test_reject_mixed_range_and_from_to(self) -> None:
        with self.assertRaisesRegex(ValueError, "either --range or --from/--to"):
            _build_git_diff_command("main..HEAD", "main", "HEAD")

    def test_reject_to_without_from(self) -> None:
        with self.assertRaisesRegex(ValueError, "--to requires --from"):
            _build_git_diff_command(None, None, "HEAD")


if __name__ == "__main__":
    unittest.main()

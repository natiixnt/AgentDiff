import unittest
from pathlib import Path

from agentdiff.diff_parser import parse_git_diff


class DiffParserTests(unittest.TestCase):
    def test_parse_git_diff_detects_files_and_rename(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        changes = parse_git_diff(diff_text)

        self.assertEqual(len(changes), 6)

        rename = next(change for change in changes if change.status == "renamed")
        self.assertEqual(rename.old_path, "src/legacy/auth_helpers.py")
        self.assertEqual(rename.new_path, "src/security/auth_utils.py")
        self.assertTrue(any("decode_token" in line for line in rename.added_lines))

    def test_parse_git_diff_detects_new_file(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        changes = parse_git_diff(diff_text)

        token_file = next(
            change for change in changes if change.new_path == "src/security/token_validator.py"
        )

        self.assertEqual(token_file.status, "added")
        self.assertEqual(token_file.old_path, "")
        self.assertGreater(len(token_file.added_lines), 10)


if __name__ == "__main__":
    unittest.main()

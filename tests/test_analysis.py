import json
import unittest
from pathlib import Path

from agentdiff.analyzer import analyze_diff


class AnalysisTests(unittest.TestCase):
    def test_analysis_flags_required_patterns(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = json.loads(Path("examples/sample_plan.json").read_text(encoding="utf-8"))

        result = analyze_diff(diff_text, plan_data)
        files = {file_data["path"]: file_data for file_data in result["files"]}

        self.assertIn("rename", files["src/security/auth_utils.py"]["patterns"])
        self.assertIn("signature_change", files["src/api/user_service.py"]["patterns"])
        self.assertIn("config_change", files["config/app.yaml"]["patterns"])
        self.assertIn("schema_change", files["migrations/20260312_add_user_role.sql"]["patterns"])
        self.assertIn("auth_related", files["src/security/token_validator.py"]["patterns"])
        self.assertIn("pattern_confidence", files["src/security/token_validator.py"])
        self.assertGreater(files["src/security/token_validator.py"]["pattern_confidence"]["auth_related"], 0.6)

    def test_analysis_produces_groups_and_review_order(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = json.loads(Path("examples/sample_plan.json").read_text(encoding="utf-8"))

        result = analyze_diff(diff_text, plan_data)

        self.assertEqual(result["summary"]["total_files"], 6)
        self.assertGreaterEqual(result["summary"]["total_groups"], 3)
        self.assertGreaterEqual(len(result["groups"]), 3)
        self.assertTrue(result["review_order"])
        self.assertEqual(result["review_order"][0]["path"], "src/security/auth_utils.py")

    def test_analysis_reports_plan_drift(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = {
            "steps": [
                {
                    "name": "Only auth utilities",
                    "files": ["src/security/auth_utils.py", "src/missing/not_changed.py"],
                }
            ]
        }

        result = analyze_diff(diff_text, plan_data)
        drift = result["plan_drift"]

        self.assertTrue(drift["has_plan"])
        self.assertIn("src/missing/not_changed.py", drift["planned_but_unchanged"])
        self.assertIn("src/api/user_service.py", drift["changed_but_unplanned"])
        self.assertGreater(drift["planned_but_unchanged_count"], 0)
        self.assertGreater(drift["changed_but_unplanned_count"], 0)

    def test_analysis_applies_ignore_patterns(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        result = analyze_diff(diff_text, ignore_patterns=["tests/*", "config/*"])

        paths = {file_data["path"] for file_data in result["files"]}
        self.assertNotIn("tests/test_user_service.py", paths)
        self.assertNotIn("config/app.yaml", paths)
        self.assertIn("tests/test_user_service.py", result["ignored"]["files"])
        self.assertIn("config/app.yaml", result["ignored"]["files"])


if __name__ == "__main__":
    unittest.main()

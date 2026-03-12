import json
import unittest
from pathlib import Path

from agentdiff.analyzer import analyze_diff
from agentdiff.markdown import analysis_to_markdown


class MarkdownTests(unittest.TestCase):
    def test_markdown_contains_expected_sections(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = json.loads(Path("examples/sample_plan.json").read_text(encoding="utf-8"))

        analysis = analyze_diff(diff_text, plan_data)
        markdown = analysis_to_markdown(analysis)

        self.assertIn("# AgentDiff Review Summary", markdown)
        self.assertIn("## Summary", markdown)
        self.assertIn("## Risk Hotspots", markdown)
        self.assertIn("## Suggested Review Order", markdown)
        self.assertIn("## Plan Drift", markdown)
        self.assertIn("src/security/auth_utils.py", markdown)


if __name__ == "__main__":
    unittest.main()

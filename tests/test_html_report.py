import json
import unittest
from pathlib import Path

from agentdiff.analyzer import analyze_diff
from agentdiff.html_report import analysis_to_static_html


class HtmlReportTests(unittest.TestCase):
    def test_static_html_report_embeds_assets_and_data(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = json.loads(Path("examples/sample_plan.json").read_text(encoding="utf-8"))

        analysis = analyze_diff(diff_text, plan_data)
        html = analysis_to_static_html(analysis)

        self.assertIn("window.__AGENTDIFF_ANALYSIS", html)
        self.assertIn("<style>", html)
        self.assertIn("Grouped Diff Viewer", html)
        self.assertNotIn('href="/styles.css"', html)
        self.assertNotIn('src="/app.js"', html)


if __name__ == "__main__":
    unittest.main()

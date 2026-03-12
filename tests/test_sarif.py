import json
import unittest
from pathlib import Path

from agentdiff.analyzer import analyze_diff
from agentdiff.sarif import analysis_to_sarif


class SarifTests(unittest.TestCase):
    def test_sarif_structure_and_results(self) -> None:
        diff_text = Path("examples/sample.diff").read_text(encoding="utf-8")
        plan_data = json.loads(Path("examples/sample_plan.json").read_text(encoding="utf-8"))

        analysis = analyze_diff(diff_text, plan_data)
        sarif = analysis_to_sarif(analysis)

        self.assertEqual(sarif["version"], "2.1.0")
        self.assertIn("runs", sarif)
        self.assertTrue(sarif["runs"])

        run = sarif["runs"][0]
        self.assertIn("tool", run)
        self.assertIn("results", run)
        self.assertGreater(len(run["results"]), 0)

        first_result = run["results"][0]
        self.assertIn("ruleId", first_result)
        self.assertIn("locations", first_result)
        self.assertTrue(first_result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"])

        # Ensure at least one pattern finding is emitted.
        self.assertTrue(any(r["ruleId"].startswith("agentdiff/pattern/") for r in run["results"]))


if __name__ == "__main__":
    unittest.main()

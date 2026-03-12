import unittest

from agentdiff.analyzer import analyze_diff
from agentdiff.secret_ignore import read_secret_ignore_patterns, secret_line_is_ignored


SECRET_DIFF = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,4 @@
 def get_cfg():
+    api_key = \"sk-live-1234567890abcdef\"
+    password = \"super-secret-value\"
     return {}
"""


class SecretDetectorTests(unittest.TestCase):
    def test_secret_exposure_pattern_and_risk_reason(self) -> None:
        result = analyze_diff(SECRET_DIFF)
        file_data = result["files"][0]

        self.assertIn("secret_exposure", file_data["patterns"])
        self.assertGreater(file_data["pattern_confidence"]["secret_exposure"], 0.7)
        self.assertIn("Signal: possible secret/credential exposure", file_data["risk_reasons"])

    def test_secret_ignore_patterns_suppress_detection(self) -> None:
        result = analyze_diff(SECRET_DIFF, secret_ignore_patterns=["api_key =", "password ="])
        file_data = result["files"][0]

        self.assertNotIn("secret_exposure", file_data["patterns"])

    def test_secret_ignore_parser_supports_plain_and_regex(self) -> None:
        self.assertTrue(secret_line_is_ignored('password = "abc"', ["password ="]))
        self.assertTrue(secret_line_is_ignored('token = "abc"', [r're:token\s*=\s*".*"']))

        # Ensure parser reads only meaningful lines.
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".agentdiff-secrets-ignore"
            path.write_text("# comment\n\npassword =\nre:token.*\n", encoding="utf-8")
            patterns = read_secret_ignore_patterns(str(path))

        self.assertEqual(patterns, ["password =", "re:token.*"])


if __name__ == "__main__":
    unittest.main()

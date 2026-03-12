import json
import unittest
from pathlib import Path

from agentdiff.analyzer import analyze_diff
from agentdiff.plugins import load_plugins


TODO_DIFF = """diff --git a/src/sample.py b/src/sample.py
index 1111111..2222222 100644
--- a/src/sample.py
+++ b/src/sample.py
@@ -1,2 +1,3 @@
 def calc(x):
+    # TODO: remove temporary branch
     return x
"""


class PluginTests(unittest.TestCase):
    def test_load_plugins_from_example_config(self) -> None:
        config_path = Path("examples/plugins/plugins.example.json")
        plugins = load_plugins(str(config_path))

        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].name, "todo-detector")

    def test_plugin_signals_merge_into_analysis(self) -> None:
        plugins = load_plugins("examples/plugins/plugins.example.json")
        result = analyze_diff(TODO_DIFF, plugins=plugins)
        file_data = result["files"][0]

        self.assertIn("todo_marker", file_data["patterns"])
        self.assertGreaterEqual(file_data["pattern_confidence"].get("todo_marker", 0), 0.7)

        reasons = " ".join(file_data["risk_reasons"])
        self.assertIn("Plugin(todo_detector)", reasons)

    def test_missing_plugin_config_is_noop(self) -> None:
        plugins = load_plugins("/tmp/definitely_missing_agentdiff_plugins_config.json")
        self.assertEqual(plugins, [])


if __name__ == "__main__":
    unittest.main()

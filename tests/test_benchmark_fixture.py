import unittest
from pathlib import Path


class BenchmarkFixtureTests(unittest.TestCase):
    def test_large_fixture_contains_at_least_500_files(self) -> None:
        diff_text = Path("benchmarks/fixtures/large_500.diff").read_text(encoding="utf-8")
        changed_files = diff_text.count("diff --git ")
        self.assertGreaterEqual(changed_files, 500)


if __name__ == "__main__":
    unittest.main()

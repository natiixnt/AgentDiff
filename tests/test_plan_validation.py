import unittest

from agentdiff.plan_validator import validate_execution_plan


class PlanValidationTests(unittest.TestCase):
    def test_valid_plan(self) -> None:
        plan = {
            "version": "1.0",
            "steps": [
                {
                    "name": "Update auth",
                    "files": ["src/security/auth_utils.py"],
                    "intent": "harden auth checks",
                }
            ],
        }
        validate_execution_plan(plan)

    def test_invalid_plan_missing_steps(self) -> None:
        with self.assertRaisesRegex(ValueError, "steps"):
            validate_execution_plan({})

    def test_invalid_plan_bad_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "files"):
            validate_execution_plan(
                {
                    "steps": [
                        {
                            "name": "Bad",
                            "files": ["ok.py", ""],
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()

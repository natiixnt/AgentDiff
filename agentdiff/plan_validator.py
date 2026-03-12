from __future__ import annotations

from typing import Any


def validate_execution_plan(plan: dict[str, Any]) -> None:
    if not isinstance(plan, dict):
        raise ValueError("Execution plan JSON must be an object")

    if "version" in plan and not isinstance(plan["version"], str):
        raise ValueError("Execution plan field `version` must be a string")

    steps = plan.get("steps")
    if steps is None:
        raise ValueError("Execution plan must include a `steps` array")
    if not isinstance(steps, list):
        raise ValueError("Execution plan field `steps` must be an array")

    for index, step in enumerate(steps):
        pointer = f"steps[{index}]"
        if not isinstance(step, dict):
            raise ValueError(f"Execution plan field `{pointer}` must be an object")

        name = step.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Execution plan field `{pointer}.name` must be a non-empty string")

        files = step.get("files")
        if not isinstance(files, list):
            raise ValueError(f"Execution plan field `{pointer}.files` must be an array of strings")

        for file_index, path in enumerate(files):
            if not isinstance(path, str) or not path.strip():
                raise ValueError(
                    f"Execution plan field `{pointer}.files[{file_index}]` must be a non-empty string"
                )

        if "intent" in step and not isinstance(step["intent"], str):
            raise ValueError(f"Execution plan field `{pointer}.intent` must be a string")

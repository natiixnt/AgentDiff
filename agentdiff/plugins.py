from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class LoadedPlugin:
    name: str
    path: Path
    analyze_file: Callable[[dict[str, Any]], dict[str, Any]]


def _load_plugin_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load plugin module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins(config_path: str | None = None) -> list[LoadedPlugin]:
    path = Path(config_path) if config_path else Path(".agentdiff.plugins.json")
    if not path.exists():
        return []

    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Plugin config must be a JSON object")

    raw_plugins = parsed.get("plugins", [])
    if not isinstance(raw_plugins, list):
        raise ValueError("Plugin config field `plugins` must be an array")

    loaded: list[LoadedPlugin] = []
    for index, item in enumerate(raw_plugins):
        if not isinstance(item, dict):
            raise ValueError(f"Plugin entry at index {index} must be an object")

        plugin_path = item.get("path")
        if not isinstance(plugin_path, str) or not plugin_path.strip():
            raise ValueError(f"Plugin entry at index {index} is missing non-empty `path`")

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            name = f"plugin_{index + 1}"

        resolved_path = (path.parent / plugin_path).resolve()
        if not resolved_path.exists():
            raise ValueError(f"Plugin `{name}` path not found: {resolved_path}")

        module = _load_plugin_module(resolved_path, f"agentdiff_plugin_{index}_{name}")
        analyze_file = getattr(module, "analyze_file", None)
        if not callable(analyze_file):
            raise ValueError(f"Plugin `{name}` must define callable `analyze_file(file_data)`")

        loaded.append(LoadedPlugin(name=name, path=resolved_path, analyze_file=analyze_file))

    return loaded

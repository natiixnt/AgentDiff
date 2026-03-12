from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_web_asset(name: str) -> str:
    root = Path(__file__).resolve().parent.parent
    return (root / "web" / name).read_text(encoding="utf-8")


def analysis_to_static_html(analysis: dict[str, Any]) -> str:
    template = _read_web_asset("index.html")
    css = _read_web_asset("styles.css")
    js = _read_web_asset("app.js")

    payload = json.dumps(analysis, separators=(",", ":")).replace("</", "<\\/")

    html = template
    html = html.replace(
        '<link rel="stylesheet" href="/styles.css" />',
        f"<style>\n{css}\n</style>",
    )

    bootstrap_script = (
        "<script>window.__AGENTDIFF_ANALYSIS = "
        + payload
        + ";</script>\n<script>\n"
        + js
        + "\n</script>"
    )
    html = html.replace('<script src="/app.js"></script>', bootstrap_script)

    return html

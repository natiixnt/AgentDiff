from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .analyzer import analyze_diff
from .ignore import read_ignore_patterns
from .plan_validator import validate_execution_plan
from .webserver import run_server


def _read_text(path: str | None) -> str:
    if path is None:
        completed = subprocess.run(
            ["git", "diff", "--find-renames"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Failed to run git diff")
        return completed.stdout
    return Path(path).read_text(encoding="utf-8")


def _read_plan(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    raw = Path(path).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    validate_execution_plan(parsed)
    return parsed


def _resolve_ignore_patterns(ignore_file_path: str | None) -> list[str]:
    if ignore_file_path:
        return read_ignore_patterns(ignore_file_path)
    return read_ignore_patterns()


def _write_output(payload: dict[str, Any], output_path: str | None) -> None:
    rendered = json.dumps(payload, indent=2)
    if output_path:
        Path(output_path).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentdiff",
        description="Analyze git diffs with higher-level change grouping and risk hints.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a diff and print JSON output")
    analyze_parser.add_argument("--diff", help="Path to a git diff file. Defaults to current `git diff`.")
    analyze_parser.add_argument("--plan", help="Optional execution plan JSON path")
    analyze_parser.add_argument("--output", help="Optional output file for analysis JSON")
    analyze_parser.add_argument(
        "--ignore-file",
        help="Path to .agentdiffignore-style file (default: ./.agentdiffignore if present)",
    )

    serve_parser = subparsers.add_parser("serve", help="Start local web UI for diff analysis")
    serve_parser.add_argument("--diff", help="Path to a git diff file. Defaults to current `git diff`.")
    serve_parser.add_argument("--plan", help="Optional execution plan JSON path")
    serve_parser.add_argument(
        "--ignore-file",
        help="Path to .agentdiffignore-style file (default: ./.agentdiffignore if present)",
    )
    serve_parser.add_argument(
        "--analysis",
        help="Path to precomputed analysis JSON (skips diff parsing)",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", default=8765, type=int, help="Bind port (default: 8765)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            diff_text = _read_text(args.diff)
            plan_data = _read_plan(args.plan)
            ignore_patterns = _resolve_ignore_patterns(args.ignore_file)
            result = analyze_diff(diff_text, plan_data, ignore_patterns=ignore_patterns)
            _write_output(result, args.output)
            return 0

        if args.command == "serve":
            if args.analysis:
                analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
            else:
                diff_text = _read_text(args.diff)
                plan_data = _read_plan(args.plan)
                ignore_patterns = _resolve_ignore_patterns(args.ignore_file)
                analysis = analyze_diff(diff_text, plan_data, ignore_patterns=ignore_patterns)
            run_server(analysis, host=args.host, port=args.port)
            return 0

        parser.print_help()
        return 1
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"agentdiff error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

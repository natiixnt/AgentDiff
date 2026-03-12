from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentdiff.analyzer import analyze_diff


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark AgentDiff analysis runtime")
    parser.add_argument("--diff", default="benchmarks/fixtures/large_500.diff", help="Diff fixture path")
    parser.add_argument("--min-files", type=int, default=500, help="Minimum expected changed files")
    parser.add_argument("--max-seconds", type=float, default=None, help="Optional fail threshold")
    args = parser.parse_args()

    diff_path = Path(args.diff)
    diff_text = diff_path.read_text(encoding="utf-8")

    start = time.perf_counter()
    analysis = analyze_diff(diff_text)
    elapsed = time.perf_counter() - start

    rendered = json.dumps(analysis, separators=(",", ":"))
    output_bytes = len(rendered.encode("utf-8"))
    total_files = int(analysis.get("summary", {}).get("total_files", 0))

    result = {
        "fixture": str(diff_path),
        "total_files": total_files,
        "elapsed_seconds": round(elapsed, 4),
        "output_bytes": output_bytes,
        "output_megabytes": round(output_bytes / (1024 * 1024), 4),
    }

    print(json.dumps(result, indent=2))

    if total_files < args.min_files:
        raise SystemExit(f"benchmark failed: expected at least {args.min_files} files, got {total_files}")

    if args.max_seconds is not None and elapsed > args.max_seconds:
        raise SystemExit(
            f"benchmark failed: elapsed {elapsed:.4f}s exceeds max {args.max_seconds:.4f}s"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path


def generate_diff(file_count: int) -> str:
    chunks: list[str] = []
    for index in range(1, file_count + 1):
        module = f"module_{index:04d}.py"
        path = f"src/bench/{module}"
        chunks.append(
            "\n".join(
                [
                    f"diff --git a/{path} b/{path}",
                    "index 1111111..2222222 100644",
                    f"--- a/{path}",
                    f"+++ b/{path}",
                    "@@ -1,2 +1,3 @@",
                    f" def fn_{index:04d}(value):",
                    "-    return value",
                    "+    # benchmark change",
                    "+    return value + 1",
                    "",
                ]
            )
        )
    return "".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic benchmark git diff")
    parser.add_argument("--files", type=int, default=500, help="Number of changed files")
    parser.add_argument(
        "--output",
        default="benchmarks/fixtures/large_500.diff",
        help="Output diff file path",
    )
    args = parser.parse_args()

    content = generate_diff(args.files)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {args.files} files to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

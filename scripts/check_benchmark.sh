#!/usr/bin/env bash
set -euo pipefail

python3 benchmarks/run_benchmark.py --diff benchmarks/fixtures/large_500.diff --min-files 500 --max-seconds 8.0

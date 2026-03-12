# Benchmark Baseline

Date: 2026-03-12

Fixture:
- `benchmarks/fixtures/large_500.diff` (500 changed files)

Result snapshot:
- elapsed seconds: `0.4358`
- output bytes: `537073`
- output MB: `0.5122`

Command:

```bash
python3 benchmarks/run_benchmark.py --diff benchmarks/fixtures/large_500.diff --min-files 500
```

CI check script:

```bash
./scripts/check_benchmark.sh
```

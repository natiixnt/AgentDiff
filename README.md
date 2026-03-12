# AgentDiff

**A diff viewer built for reviewing coding-agent changes.**

AgentDiff helps you review AI-generated pull requests faster by turning raw line diffs into higher-level change intent: what changed, which files are connected, and where the risk is.

## Hook

Coding agents can edit many files at once, mix refactors with behavior changes, and touch sensitive surfaces (auth, config, schema) in a single run.

AgentDiff gives you a reviewer-oriented view of that output:

- grouped logical change sets
- change type hints (rename, refactor, extraction, behavior change)
- confidence scores for each detected change signal
- AST-aware Python rename/refactor classification fallback
- risk annotations with reasons
- suggested review order
- plan-vs-diff drift flags (planned-but-unchanged, changed-but-unplanned)
- monorepo-aware workspace grouping
- related-file context
- unified/side-by-side diff mode with optional scroll sync

## Why `git diff` Is Not Enough for Agent Changes

`git diff` is excellent for line-level inspection, but coding-agent output usually needs more structure for safe review:

- agent edits are often cross-file and cross-layer, while line diffs are file-local
- one generated patch can include multiple intents (cleanup + feature + config tweak)
- risky surfaces are easy to miss without explicit signals
- review sequencing matters more when edits are broad and fast

AgentDiff keeps the line-level patch, but adds semantic grouping and risk-first triage.

## Screenshots

Placeholders for UI screenshots:

![Summary panel placeholder](docs/screenshots/summary-panel.png)
![Grouped diff viewer placeholder](docs/screenshots/grouped-diff-viewer.png)
![Risk sidebar placeholder](docs/screenshots/risk-sidebar.png)
![Related files placeholder](docs/screenshots/related-files.png)

## Demo Example

Run the included sample diff and execution plan:

```bash
agentdiff analyze --diff examples/sample.diff --plan examples/sample_plan.json
```

Start the local UI:

```bash
agentdiff serve --diff examples/sample.diff --plan examples/sample_plan.json --port 8765
```

Open `http://127.0.0.1:8765`.

What the demo highlights:

- auth-related edits grouped together
- schema and config changes identified explicitly
- review order seeded from the execution plan and risk scoring

## Install

### Prerequisites

- Python 3.10+

### From source

```bash
git clone <your-repo-url>
cd AgentDiff
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quickstart

Analyze current local changes:

```bash
agentdiff analyze
```

Use ignore patterns from `.agentdiffignore` automatically (or pass a custom path):

```bash
agentdiff analyze --ignore-file .agentdiffignore
```

Analyze a specific diff and write JSON output:

```bash
agentdiff analyze --diff examples/sample.diff --plan examples/sample_plan.json --output analysis.json
```

Export SARIF for CI annotation pipelines:

```bash
agentdiff analyze --diff examples/sample.diff --format sarif --output agentdiff.sarif.json
```

Serve the web app from precomputed analysis:

```bash
agentdiff serve --analysis analysis.json
```

Keyboard shortcuts in UI:

- `?` open/close help
- `j/k` next/previous file
- `[/]` next/previous group
- `o` toggle current group

Review state is persisted locally per diff view:

- collapsed/expanded groups
- visited file markers
- optional per-file reviewer notes
- resettable with the `Reset State` button

## Architecture

AgentDiff is intentionally lightweight: Python stdlib backend + minimal static frontend.

### High-level flow

1. Parse git diff into file change objects.
2. Detect patterns (rename, signature/config/schema/auth signals).
3. Classify change type and score risk.
4. Group related files into logical review sets (workspace-aware in monorepos).
5. Attach detector confidence per pattern.
6. Compute plan drift (when execution plan is provided).
7. Suggest review order (plan-aware when provided).
8. Render analysis in local web UI.

### Repository structure

- `agentdiff/`: CLI, diff parser, analysis orchestration, local web server
- `analyzers/`: categorization, pattern detection, grouping, risk, related-files logic
- `schemas/`: versioned schemas (`execution_plan.v1.json`)
- `web/`: static UI (`index.html`, `app.js`, `styles.css`)
- `examples/`: sample diff, optional plan, sample analysis output
- `tests/`: parser and analyzer tests

## Roadmap

- Expand AST heuristics beyond current Python-focused strategy
- Add inline risk explanations directly inside diff hunks
- Add side-by-side and per-group filtering in UI
- Add plugin-style detectors for language/framework-specific patterns
- Add SARIF/CI output mode for automated review gates
- Add richer rename/extraction confidence scoring

## Confidence Scale

Pattern confidence values are heuristic probabilities in the range `0.00` to `1.00`:

- `0.85 - 1.00`: very likely signal
- `0.65 - 0.84`: probable signal
- `0.40 - 0.64`: weak signal, review carefully
- `< 0.40`: low-confidence hint

These scores are intended to prioritize human review, not to act as hard truth.

## CI Example (SARIF)

Generate SARIF and upload it in your CI system:

```bash
agentdiff analyze --format sarif --output agentdiff.sarif.json
```

Use your platform SARIF uploader (for example, GitHub code scanning upload action) to attach findings to PRs.

## License

MIT. See [LICENSE](LICENSE).

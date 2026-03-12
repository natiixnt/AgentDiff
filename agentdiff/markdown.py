from __future__ import annotations

from typing import Any


def _line(label: str, value: Any) -> str:
    return f"- **{label}:** {value}"


def analysis_to_markdown(analysis: dict[str, Any]) -> str:
    summary = analysis.get("summary", {})
    files = analysis.get("files", [])
    review_order = analysis.get("review_order", [])
    drift = analysis.get("plan_drift", {})

    lines: list[str] = []
    lines.append("# AgentDiff Review Summary")
    lines.append("")
    lines.append("## Summary")
    lines.append(_line("Files", summary.get("total_files", 0)))
    lines.append(_line("Groups", summary.get("total_groups", 0)))
    lines.append(_line("Additions", summary.get("total_additions", 0)))
    lines.append(_line("Deletions", summary.get("total_deletions", 0)))

    risk_levels = summary.get("risk_levels", {})
    if isinstance(risk_levels, dict):
        lines.append(_line("High risk files", risk_levels.get("high", 0)))
        lines.append(_line("Medium risk files", risk_levels.get("medium", 0)))
        lines.append(_line("Low risk files", risk_levels.get("low", 0)))

    lines.append("")
    lines.append("## Risk Hotspots")

    sorted_files = sorted(
        files,
        key=lambda item: (-int(item.get("risk_score", 0)), str(item.get("path", ""))),
    )
    hotspots = [file_data for file_data in sorted_files if file_data.get("risk_level") in {"high", "medium"}][:8]

    if not hotspots:
        lines.append("- No medium/high-risk hotspots detected.")
    else:
        for file_data in hotspots:
            path = file_data.get("path", "<unknown>")
            risk = file_data.get("risk_level", "low")
            score = file_data.get("risk_score", 1)
            reasons = file_data.get("risk_reasons", [])
            reason_text = "; ".join(reasons) if reasons else "No explicit reasons"
            lines.append(f"- `{path}` — {risk} ({score}/10): {reason_text}")

    lines.append("")
    lines.append("## Suggested Review Order")
    if not review_order:
        lines.append("1. No review-order suggestions available")
    else:
        for index, item in enumerate(review_order[:20], start=1):
            path = item.get("path", "<unknown>")
            reason = item.get("reason", "")
            risk = item.get("risk", "low")
            lines.append(f"{index}. `{path}` ({risk}) — {reason}")

    if drift.get("has_plan"):
        lines.append("")
        lines.append("## Plan Drift")
        lines.append(
            f"- Planned but unchanged: {drift.get('planned_but_unchanged_count', 0)}"
        )
        lines.append(
            f"- Changed but unplanned: {drift.get('changed_but_unplanned_count', 0)}"
        )

        planned_but_unchanged = drift.get("planned_but_unchanged", [])
        changed_but_unplanned = drift.get("changed_but_unplanned", [])

        if planned_but_unchanged:
            lines.append("- Planned but unchanged files:")
            for path in planned_but_unchanged[:10]:
                lines.append(f"  - `{path}`")

        if changed_but_unplanned:
            lines.append("- Changed but unplanned files:")
            for path in changed_but_unplanned[:10]:
                lines.append(f"  - `{path}`")

    return "\n".join(lines).rstrip() + "\n"

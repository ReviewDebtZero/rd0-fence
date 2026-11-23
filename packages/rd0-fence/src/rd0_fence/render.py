"""Text and Markdown output for a scope report."""

from __future__ import annotations

from .scope import Report

MARKER = "<!-- rd0_fence:v1 -->"


def text(rep: Report) -> str:
    lines = [
        f"fence: {len(rep.flagged)} part(s) outside the issue's scope, "
        f"{rep.out_lines}/{rep.total_lines} changed lines ({rep.out_fraction:.0%})"
    ]
    if not rep.anchored:
        lines.append("  note: the issue names no file, symbol or matching term; only CI, dependency and")
        lines.append("        formatting changes can be judged")
    for p in rep.flagged:
        where = f"{p.path} {p.hunk}" if p.hunk else p.path
        lines.append(f"  [{p.severity}] {where} (+/-{p.lines}): {p.reason}")
    return "\n".join(lines)


def markdown(rep: Report, issue_ref: str = "the linked issue") -> str:
    flagged = sorted(rep.flagged, key=lambda p: (p.severity != "high", -p.lines))
    lines = [
        MARKER,
        f"**Fence:** {len(flagged)} part(s) of this PR go beyond what {issue_ref} asked for "
        f"({rep.out_lines} of {rep.total_lines} changed lines, {rep.out_fraction:.0%}).",
        "",
        "| Part | Lines | Why it looks out of scope |",
        "|---|---:|---|",
    ]
    for p in flagged:
        where = f"`{p.path}` {p.hunk}" if p.hunk else f"`{p.path}`"
        lines.append(f"| {where} | {p.lines} | {p.reason} |")
    lines += [
        "",
        "_Automated hint from [rd0-fence](https://github.com/ReviewDebtZero/rd0-fence), not a decision. "
        "If a part is needed, say why in the PR description or split it into its own PR._",
    ]
    return "\n".join(lines)

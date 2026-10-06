"""Scoreboard: one markdown table per run, previous run beside it (EVAL.md).

Run: uv run python scripts/eval/scoreboard.py eval/runs/<label> [--prev eval/runs/<old>]
Reads results.json (gates table from gates.py --write, grading tallies) plus
per-PR receipts and video durations from outputs/pr<N>/run.json.
Writes scoreboard.md: gates passed, per-PR receipts, video durations,
per-condition comprehension (correct/partial/wrong/cannot-tell), misleading
answers, and the C0 baseline beside it.
Comprehension numbers come from results.json only; missing grades render
as "not scored".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CONDITIONS = ["c0", "c1", "c2", "c3", "c4", "c5"]

BASELINE_RUN = "2026-10-06-baseline"
BASELINE_C0 = "32.3% (31/96)"


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}% ({n}/{total})" if total else "—"


def _grade_cell(tally: dict | None) -> str:
    if not tally:
        return "not scored"
    total = sum(int(tally.get(k, 0)) for k in ("correct", "partial", "wrong", "cannot_tell"))
    parts = " / ".join(
        f"{k} {_pct(int(tally.get(k, 0)), total)}"
        for k in ("correct", "partial", "wrong", "cannot_tell")
    )
    return parts


def _gates_line(gates: dict | None) -> str:
    if not gates:
        return "gates: not scored"
    prs = sorted(gates)
    passed = sum(1 for pr in prs for cell in gates[pr].values() if cell.get("pass"))
    possible = sum(len(gates[pr]) for pr in prs)
    failed = [f"{pr}/{g}" for pr in prs for g, cell in gates[pr].items() if not cell.get("pass")]
    line = f"gates passed: {passed}/{possible} across {len(prs)} PRs"
    if failed:
        line += f"; failures: {', '.join(failed)}"
    return line


def _receipts_table(run_dir: Path) -> str:
    rows = []
    for pr_dir in sorted((run_dir / "outputs").iterdir()):
        if not pr_dir.is_dir():
            continue
        run_path = pr_dir / "run.json"
        if not run_path.exists():
            rows.append(f"| {pr_dir.name} | — | — |")
            continue
        run = json.loads(run_path.read_text())
        check = run.get("check", {})
        receipts = check.get("receipts", "—")
        duration = run.get("duration_seconds", "—")
        if isinstance(duration, float):
            duration = f"{duration:.1f}s"
        rows.append(f"| {pr_dir.name} | {receipts} | {duration} |")
    body = "\n".join(rows) if rows else "| — | — | — |"
    return f"| PR | receipts | video duration |\n|----|---|---|---|\n{body}"


def build_scoreboard(run_dir: Path, prev_dir: Path | None = None) -> str:
    results_path = run_dir / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}
    gates = results.get("gates")
    grades = results.get("grades", {})

    lines = [f"# Scoreboard: {run_dir.name}", ""]
    lines.append(_gates_line(gates))
    lines.append("")
    lines.append("## Per-PR receipts and video durations")
    lines.append("")
    lines.append(_receipts_table(run_dir))
    lines.append("")
    lines.append("## Comprehension by condition")
    lines.append("")
    lines.append("| condition | correct / partial / wrong / cannot-tell |")
    lines.append("|---|---|")
    for cond in CONDITIONS:
        lines.append(f"| {cond.upper()} | {_grade_cell(grades.get(cond))} |")
    misleading = sum(int(t.get("wrong", 0)) for c, t in grades.items() if c != "c0")
    lines.append("")
    lines.append(f"misleading answers (wrong from C1-C5): {misleading}")
    lines.append("")
    lines.append(f"## C0 baseline beside it ({BASELINE_RUN})")
    lines.append("")
    c0 = grades.get("c0")
    lines.append(f"C0 this run: {_grade_cell(c0)}; frozen baseline C0 overall: {BASELINE_C0}.")
    if prev_dir is not None:
        prev_path = prev_dir / "results.json"
        prev = json.loads(prev_path.read_text()) if prev_path.exists() else {}
        lines.append("")
        lines.append(f"## Previous run beside it ({prev_dir.name})")
        lines.append("")
        lines.append(_gates_line(prev.get("gates")))
        prev_grades = prev.get("grades", {})
        for cond in CONDITIONS:
            lines.append(f"- {cond.upper()} prev: {_grade_cell(prev_grades.get(cond))}")
    lines.append("")
    lines.append("## Failures")
    lines.append("")
    failed = [
        f"{pr}/{g}"
        for pr, row in (gates or {}).items()
        for g, cell in row.items()
        if not cell.get("pass")
    ]
    lines.append(("None." if not failed else "; ".join(failed)) + "")
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scoreboard.py <run_dir> [--prev <old_run_dir>]")
        return 2
    run_dir = Path(sys.argv[1])
    prev_dir = None
    if "--prev" in sys.argv:
        prev_dir = Path(sys.argv[sys.argv.index("--prev") + 1])
    out = run_dir / "scoreboard.md"
    out.write_text(build_scoreboard(run_dir, prev_dir))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

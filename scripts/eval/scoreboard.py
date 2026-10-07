"""Scoreboard: one markdown table per run, previous run beside it (EVAL.md).

Run: uv run python scripts/eval/scoreboard.py eval/runs/<label> [--prev eval/runs/<old>]
Reads results.json (gates table from gates.py --write, grading tallies) plus
per-PR receipts and video durations from outputs/pr<N>/run.json.
Writes scoreboard.md: gates passed, per-PR receipts, video durations,
per-condition comprehension (correct/partial/wrong/cannot-tell), misleading
answers, and the C0 baseline beside it.
Final comprehension grades come from grades/reviewer-*.json. The frozen
question sets define completeness. Invalid grades stop generation before any write.
results.json remains unchanged. Missing evidence never counts as a pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CONDITIONS = ["c0", "c1", "c2", "c3", "c4", "c5"]

BASELINE_RUN = "2026-10-06-baseline"
BASELINE_C0 = "32.3% (31/96)"
BASELINE_CORRECT = 31 / 96 * 100
TARGETS = {"c1": 35, "c2": 60, "c3": 70, "c4": 85}
VERDICTS = ("correct", "partial", "wrong", "cannot_tell")
QUESTIONS = Path(__file__).resolve().parents[2] / "eval/questions"


def _final_grades(run_dir: Path) -> tuple[dict[str, dict[str, int]], str]:
    paths = sorted((run_dir / "grades").glob("reviewer-*.json"))
    if not paths:
        return {}, "missing final grades"
    expected = {
        (data["pr"], cond, q["id"])
        for path in QUESTIONS.glob("pr*.json")
        for data in [json.loads(path.read_text())]
        for cond in CONDITIONS[1:]
        for q in data["questions"]
    }
    grades: dict[tuple[int, str, str], str] = {}
    for path in paths:
        data = json.loads(path.read_text())
        for grade in data["grades"]:
            key = (grade["pr"], grade["condition"], grade["question"])
            if key not in expected:
                raise ValueError(f"unknown grade {key} in {path}")
            if key in grades:
                raise ValueError(f"duplicate grade {key} in {path}")
            verdict = grade["verdict"]
            if verdict not in VERDICTS:
                raise ValueError(f"invalid verdict {verdict!r} for {key} in {path}")
            if grade["pr"] not in data["prs"]:
                raise ValueError(f"reviewer PR mismatch for {key} in {path}")
            grades[key] = verdict
    missing = expected - grades.keys()
    if missing:
        raise ValueError(f"missing {len(missing)} final grades: {sorted(missing)}")
    tallies = {cond: dict.fromkeys(VERDICTS, 0) for cond in CONDITIONS[1:]}
    for (_, cond, _), verdict in grades.items():
        tallies[cond][verdict] += 1
    sources = ", ".join(f"[grades/{p.name}](grades/{p.name})" for p in paths)
    return (
        tallies,
        f"Final grades complete: {len(grades)}/{len(expected)} unique PR/condition/question entries. Sources: {sources}.",
    )


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}% ({n}/{total})" if total else "—"


def _grade_cell(tally: dict[str, int] | None) -> str:
    if not tally:
        return "not scored"
    total = sum(int(tally.get(k, 0)) for k in ("correct", "partial", "wrong", "cannot_tell"))
    parts = " / ".join(
        f"{k} {_pct(int(tally.get(k, 0)), total)}"
        for k in ("correct", "partial", "wrong", "cannot_tell")
    )
    return parts


def _c0_grades(results: dict[str, Any]) -> dict[str, int] | None:
    if "c0" in results.get("grades", {}):
        tally: dict[str, int] = results["grades"]["c0"]
        return tally
    verdicts = [
        verdict
        for pr, row in results.items()
        if pr.startswith("pr") and isinstance(row, dict)
        for verdict in row.get("conditions", {}).get("c0", {}).get("verdicts", {}).values()
    ]
    return {v: verdicts.count(v) for v in VERDICTS} if verdicts else None


def _gates_line(gates: dict[str, Any] | None) -> str:
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
    for pr_dir in sorted((run_dir / "outputs").glob("*")):
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
    return f"| PR | receipts | video duration |\n|----|---|---|\n{body}"


def _evidence(run_dir: Path, results: dict[str, Any]) -> list[str]:
    audits = sorted((run_dir / "audit").glob("pr*.json"))
    confirmed = 0
    stale = []
    for path in audits:
        audit = json.loads(path.read_text())
        confirmed += sum(v.get("verdict") == "confirmed" for v in audit.get("verdicts", []))
        board_path = run_dir / "boards" / path.name
        board = json.loads(board_path.read_text()) if board_path.exists() else {}
        statements = {
            say if isinstance(say, str) else say["show"]
            for scene in board.get("scenes", [])
            for say in scene.get("say", [])
        }
        old = sum(f.get("statement") not in statements for f in audit.get("findings", []))
        if old:
            stale.append(
                f"[{path.stem}](audit/{path.name}) ({old} original statements absent from current board)"
            )
    lines = [
        f"Grounding audit files: {len(audits)}. Recorded confirmed verdicts: {confirmed}. "
        "These files have no artifact hashes. Current-output validity is unverified.",
    ]
    if stale:
        lines.append("stale audit findings: " + "; ".join(stale) + ".")
    if confirmed:
        lines.append(
            f"Recorded audit failures: {confirmed} confirmed verdicts in [audit files](audit/). "
            "These are not a verified count for current outputs."
        )
    if not audits:
        lines.append("missing grounding audit evidence.")
    for key, label, target in (
        ("judge", "judge", "at least 2 of 3 planted false statements detected"),
        ("ocr", "OCR", "31/31 at 800 px"),
        ("arrow_precision", "arrow", "at least 99% on the 28 public PRs"),
        ("human", "human", "adoption on at least 2 of 3 PRs and grader agreement at least 8/10"),
    ):
        if key not in results:
            lines.append(f"missing {label} evidence for this run. Target: {target}.")
        else:
            lines.append(
                f"{label} evidence recorded in [results.json](results.json): "
                f"`{json.dumps(results[key], sort_keys=True)}`. Validity is unverified."
            )
    lines.append(
        "Historical OCR 28/31 at 800 px and arrow precision 879/882 are not measurements of this run."
    )
    lines.append(
        "The [human session sheet](../../human/2026-10-07.md) is a template, not completed evidence."
    )
    return lines


def build_scoreboard(run_dir: Path, prev_dir: Path | None = None) -> str:
    results_path = run_dir / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}
    gates = results.get("gates")
    grades, completeness = _final_grades(run_dir)
    c0 = _c0_grades(results)
    failures = []

    lines = [f"# Scoreboard: {run_dir.name}", ""]
    lines.append(_gates_line(gates))
    lines.append("")
    lines.append("## Per-PR receipts and video durations")
    lines.append("")
    lines.append(_receipts_table(run_dir))
    lines.append("")
    lines.append("## Comprehension by condition")
    lines.append("")
    lines.append(completeness)
    lines.append("")
    lines.append("| condition | correct / partial / wrong / cannot-tell |")
    lines.append("|---|---|")
    for cond in CONDITIONS:
        lines.append(
            f"| {cond.upper()} | {_grade_cell(c0 if cond == 'c0' else grades.get(cond))} |"
        )
    misleading = str(sum(t["wrong"] for t in grades.values())) if grades else "not scored"
    lines.append("")
    lines.append(f"misleading answers (wrong from C1-C5): {misleading}")
    lines.append("")
    lines.append(f"## C0 baseline beside it ({BASELINE_RUN})")
    lines.append("")
    lines.append(f"C0 this run: {_grade_cell(c0)}; frozen baseline C0 overall: {BASELINE_C0}.")
    lines.extend(
        [
            "",
            "## Frozen targets",
            "",
            "Targets remain frozen in the [baseline scoreboard](../2026-10-06-baseline/scoreboard.md).",
            "",
            "| condition | absolute target | +30pt target | result |",
            "|---|---|---|---|",
        ]
    )
    for cond in CONDITIONS[1:]:
        tally = grades.get(cond)
        total = sum(tally.values()) if tally else 0
        correct = tally["correct"] / total * 100 if tally and total else None
        target = TARGETS.get(cond)
        states = []
        for label, threshold in (("absolute", target), ("+30pt", BASELINE_CORRECT + 30)):
            if threshold is None:
                continue
            state = (
                "not scored" if correct is None else "passed" if correct >= threshold else "failed"
            )
            text = f"{cond.upper()} {label} target {state}"
            states.append(text)
            if state != "passed":
                failures.append(text)
        absolute = f"{target:.1f}%" if target is not None else "not specified"
        lines.append(
            f"| {cond.upper()} | {absolute} | {BASELINE_CORRECT + 30:.1f}% | {'; '.join(states)} |"
        )
    if not grades:
        failures.append("missing final grades")
    elif misleading != "0":
        failures.append(f"misleading answers target failed: {misleading} wrong; target 0")
    lines.extend(["", "## Evidence status", ""])
    evidence = _evidence(run_dir, results)
    lines.extend(evidence)
    failures.extend(
        line
        for line in evidence
        if line.startswith(("missing", "stale", "Recorded audit failures"))
    )
    failures.append(
        "Grounding audit validity is unverified without current artifact binding and a valid judge check."
    )
    if prev_dir is not None:
        prev_path = prev_dir / "results.json"
        prev = json.loads(prev_path.read_text()) if prev_path.exists() else {}
        lines.append("")
        lines.append(f"## Previous run beside it ({prev_dir.name})")
        lines.append("")
        lines.append(_gates_line(prev.get("gates")))
        prev_grades, prev_complete = _final_grades(prev_dir)
        lines.append(prev_complete)
        for cond in CONDITIONS:
            tally = _c0_grades(prev) if cond == "c0" else prev_grades.get(cond)
            lines.append(f"- {cond.upper()} prev: {_grade_cell(tally)}")
    lines.append("")
    lines.append("## Failures")
    lines.append("")
    failed = [
        f"{pr}/{g}"
        for pr, row in (gates or {}).items()
        for g, cell in row.items()
        if not cell.get("pass")
    ]
    failures.extend(failed)
    if not gates:
        failures.append("missing gates evidence")
    lines.extend(f"- {failure}" for failure in failures)
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
    try:
        report = build_scoreboard(run_dir, prev_dir)
    except (ValueError, KeyError, TypeError) as error:
        print(f"invalid scoreboard evidence: {error}", file=sys.stderr)
        return 1
    out.write_text(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

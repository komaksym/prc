"""Deterministic grades for every answer in a scored run (EVAL.md part C).

Uses the frozen v1 question file per PR and records its filename.
New question versions require independent verification and a separate run.
Agent grading owns free text; those rows keep the NEEDS_HUMAN verdict.

Usage:
  uv run python scripts/eval/grade_round.py eval/runs/<run> [out.json]
  uv run python scripts/eval/grade_round.py eval/runs/<before> eval/runs/<after>
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import answer_map, grade_question  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def questions_for(pr: int) -> tuple[Path, dict]:
    qdir = ROOT / "eval" / "questions"
    path = qdir / f"pr{pr}.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def packet_answer_sets(run: Path) -> tuple[set[str], set[str]]:
    expected = {
        f"{path.parent.parent.name}/{path.parent.name}"
        for path in (run / "packets").glob("pr*/c*/manifest.json")
    }
    found = {f"{path.parent.name}/{path.stem}" for path in (run / "answers").glob("pr*/*.json")}
    return expected, found


def grade_run(run: Path) -> list[dict]:
    rows: list[dict] = []
    hash_path = run / "question-hashes.json"
    recorded = json.loads(hash_path.read_text(encoding="utf-8")) if hash_path.exists() else None
    expected, found = packet_answer_sets(run)
    if expected - found:
        raise ValueError(f"missing answer files: {sorted(expected - found)}")
    if expected and found - expected:
        raise ValueError(f"unexpected answer files: {sorted(found - expected)}")
    if not found:
        raise ValueError("no answer files")
    for ans_path in sorted((run / "answers").glob("pr*/*.json")):
        pr = int(ans_path.parent.name[2:])
        qpath, questions = questions_for(pr)
        digest = hashlib.sha256(qpath.read_bytes()).hexdigest()
        if recorded is not None and recorded.get(qpath.name) != digest:
            raise ValueError(f"recorded question key missing or changed: {qpath.name}")
        answers = json.loads(ans_path.read_text(encoding="utf-8"))
        by_id = answer_map(questions["questions"], answers)
        for q in questions["questions"]:
            rows.append(
                {
                    "pr": pr,
                    "condition": ans_path.stem,
                    "question": q["id"],
                    "type": q.get("type"),
                    "keys": qpath.name,
                    "key_sha256": digest,
                    "verdict": grade_question(q, by_id[q["id"]]),
                }
            )
    return rows


def summary(rows: list[dict]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        counts[(row["condition"], row["verdict"])] += 1
    return counts


def main(argv: list[str]) -> int:
    if len(argv) == 3 and Path(argv[2]).is_dir():
        before = {(r["pr"], r["condition"], r["question"]): r for r in grade_run(Path(argv[1]))}
        after = {(r["pr"], r["condition"], r["question"]): r for r in grade_run(Path(argv[2]))}
        if before.keys() != after.keys():
            raise ValueError(
                f"comparison coverage differs: missing {sorted(before.keys() - after.keys())}, "
                f"added {sorted(after.keys() - before.keys())}"
            )
        drifted = sorted(
            key for key in before if before[key].get("key_sha256") != after[key].get("key_sha256")
        )
        if drifted:
            raise ValueError(f"question key hash differs: {drifted}")
        for key in sorted(before):
            old = before[key]["verdict"]
            new = after[key]["verdict"]
            flag = "" if old == new else "  <<< CHANGED"
            print(f"{key}: {old} -> {new}{flag}")
        return 0
    run = Path(argv[1])
    expected, found = packet_answer_sets(run)
    rows = grade_run(run)
    if expected:
        print(f"packets: {len(expected & found)}/{len(expected)} answered")
    else:
        print("packets: no manifests")
    print(f"answers: {len(found)} files")
    print(f"questions: {len(rows)} rows")
    for (condition, verdict), count in sorted(summary(rows).items()):
        print(f"{condition} {verdict}: {count}")
    if len(argv) > 2:
        Path(argv[2]).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

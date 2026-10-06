"""Grade reader answers against frozen question keys (EVAL.md part C).

Deterministic types (exact, exact_code, set, set_or_none, bool, location)
are graded here after normalizing whitespace and quotes. Free text
(q1 and free-form q6) prints NEEDS_HUMAN for agent grading.

Usage: uv run python scripts/eval/grade.py eval/questions/pr12.json eval/runs/<run>/answers/pr12/c0.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CANNOT_TELL = "cannot tell"


def norm(text: str) -> str:
    return " ".join(text.strip().strip("\"'`").split())


def norm_code(text: str) -> str:
    return " ".join(text.strip().strip("\"'`").split())


def is_cannot_tell(answer: object) -> bool:
    return isinstance(answer, str) and norm(answer).lower() == CANNOT_TELL


def grade_set(key: object, answer: object) -> str:
    if isinstance(key, str) and key.lower() == "none":
        if isinstance(answer, str) and norm(answer).lower() == "none":
            return "correct"
        if isinstance(answer, list) and not answer:
            return "correct"
        return "wrong"
    expected = {norm(str(item)) for item in key} if isinstance(key, list) else {norm(str(key))}
    if isinstance(answer, str):
        got = {norm(answer)} if answer.strip() else set()
    else:
        got = {norm(str(item)) for item in (answer or [])}
    if got == expected:
        return "correct"
    if got and got <= expected:
        return "partial"
    if got & expected:
        return "partial"
    return "wrong"


def grade_location(key: str, answer: object) -> str:
    if not isinstance(answer, str):
        return "wrong"
    parts = [p.strip() for p in key.split("::")]
    hit = sum(1 for p in parts if p and p in answer)
    if hit == len(parts):
        return "correct"
    if hit:
        return "partial"
    return "wrong"


def grade_question(q: dict, answer: object) -> str:
    if is_cannot_tell(answer):
        return "cannot_tell"
    qtype = q.get("type")
    key = q.get("key")
    if qtype == "bool":
        return (
            "correct"
            if isinstance(answer, str) and norm(answer).lower() == str(key).lower()
            else "wrong"
        )
    if qtype in {"exact", "exact_code"}:
        if not isinstance(answer, str):
            return "wrong"
        return "correct" if norm_code(answer) == norm_code(str(key)) else "wrong"
    if qtype in {"set", "set_or_none"}:
        return grade_set(key, answer)
    if qtype == "location":
        return grade_location(str(key), answer)
    if qtype == "name_or_free" and isinstance(key, str) and " " not in key:
        if not isinstance(answer, str):
            return "wrong"
        return "correct" if norm_code(answer) == norm_code(key) else "wrong"
    return "NEEDS_HUMAN"


def main() -> int:
    questions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    answers = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    by_id = {a["id"]: a.get("answer") for a in answers.get("answers", [])}
    out = []
    for q in questions["questions"]:
        verdict = grade_question(q, by_id.get(q["id"]))
        out.append({"id": q["id"], "verdict": verdict})
        print(f"{q['id']}: {verdict}")
    Path(sys.argv[3]).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8") if len(
        sys.argv
    ) > 3 else None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

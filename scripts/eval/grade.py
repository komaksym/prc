"""Grade reader answers against frozen question keys (EVAL.md part C).

Deterministic types (exact, exact_code, set, set_or_none, bool, location)
are graded here after normalizing whitespace and quotes. Free text
(q1 and free-form q6) prints NEEDS_HUMAN for agent grading.

Usage: uv run python scripts/eval/grade.py eval/questions/pr12.json eval/runs/<run>/answers/pr12/c0.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CANNOT_TELL = "cannot tell"
_CANNOT_TELL_RX = re.compile(r"^cannot\s+tell(?![a-z0-9])", re.IGNORECASE)
_BOOL_TOKEN_RX = re.compile(r"^(true|false)(?![a-z0-9])", re.IGNORECASE)


def norm(text: str) -> str:
    return " ".join(text.strip().strip("\"'`").split())


def norm_code(text: str) -> str:
    return " ".join(text.strip().strip("\"'`").split())


def is_cannot_tell(answer: object) -> bool:
    if isinstance(answer, bool):
        return False
    return isinstance(answer, str) and _CANNOT_TELL_RX.search(norm(answer)) is not None


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
    want = [part for part in (norm(p) for p in key.split("::")) if part]
    got = [norm(p) for p in answer.split("::")]
    hit = sum(1 for w, g in zip(want, got, strict=False) if w == g)
    if hit == len(want) and len(got) == len(want):
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
        if isinstance(answer, bool):
            token = str(answer).lower()
        elif isinstance(answer, str):
            match = _BOOL_TOKEN_RX.search(norm(answer))
            token = match.group(1).lower() if match else ""
        else:
            token = ""
        return "correct" if token == str(key).lower() else "wrong"
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
        if " " not in norm_code(answer):
            return "correct" if norm_code(answer) == norm_code(key) else "wrong"
    return "NEEDS_HUMAN"


def answer_map(questions: list[dict], answers: dict) -> dict[str, object]:
    expected = {q["id"] for q in questions}
    items = answers.get("answers", [])
    ids = [item["id"] for item in items]
    missing = sorted(expected - set(ids))
    unknown = sorted(set(ids) - expected)
    duplicates = sorted(qid for qid in set(ids) if ids.count(qid) > 1)
    if missing or unknown or duplicates:
        raise ValueError(f"missing {missing}, unknown {unknown}, duplicate {duplicates}")
    no_answer = sorted(item.get("id", "?") for item in items if "answer" not in item)
    if no_answer:
        raise ValueError(f"missing answer field: {no_answer}")
    return {item["id"]: item.get("answer") for item in items}


def main() -> int:
    questions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    answers = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    by_id = answer_map(questions["questions"], answers)
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

"""Validate frozen comprehension question sets (PLAN Stage 1 failure checks).

Checks 1-4 run on eval/questions/pr<N>.json against the PR head blobs in the
local git caches. Check 5 flags a too-easy set once C0 results exist.

Usage: uv run python scripts/eval/validate_questions.py [--c0-results PATH]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "eval" / "questions"
CACHE_DIR = ROOT / "prototypes" / "mdp" / "store" / "git-cache"

CACHE_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_RE = re.compile(r"^(.+):(\d+)$")
EXACT_TYPES = {"exact", "exact_code"}
EXPECTED_IDS = [f"q{i}" for i in range(1, 9)]


def git(cache: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "--git-dir", str(cache), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def blob_text(cache: Path, head_sha: str, path: str) -> list[str]:
    entry = git(cache, "ls-tree", head_sha, path).strip()
    if not entry:
        raise ValueError(f"path missing at head: {path}")
    blob = entry.split()[2]
    return git(cache, "cat-file", "-p", blob).splitlines()


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    pr = data.get("pr")
    head_sha = data.get("head_sha", "")
    if data.get("version") != 1:
        errors.append(f"{path.name}: version must be 1")
    if not CACHE_RE.match(head_sha or ""):
        errors.append(f"{path.name}: head_sha is not a 40-char hex sha")
        return errors
    cache = CACHE_DIR / f"komaksym__linkedin-mdp__{pr}.git"
    if not cache.is_dir():
        errors.append(f"{path.name}: git cache missing: {cache.name}")
        return errors
    try:
        kind = git(cache, "cat-file", "-t", head_sha).strip()
    except ValueError as exc:
        errors.append(f"{path.name}: {exc}")
        return errors
    if kind != "commit":
        errors.append(f"{path.name}: head_sha is a {kind}, not a commit")

    questions = data.get("questions", [])
    ids = [q.get("id") for q in questions]
    if ids != EXPECTED_IDS:
        errors.append(f"{path.name}: ids must be q1..q8 in order, got {ids}")

    for q in questions:
        qid = q.get("id", "?")
        tag = f"{path.name} {qid}"
        evidence = q.get("evidence", [])
        # Check 1: a question has no evidence.
        if not evidence:
            errors.append(f"{tag}: no evidence")
            continue
        lines: list[str] = []
        for item in evidence:
            match = EVIDENCE_RE.match(item or "")
            if not match:
                errors.append(f"{tag}: bad evidence format: {item!r}")
                continue
            rel, lineno = match.group(1), int(match.group(2))
            try:
                text = blob_text(cache, head_sha, rel)
            except ValueError:
                # Check 2: an evidence line does not exist at the head sha.
                errors.append(f"{tag}: evidence path missing at head: {item}")
                continue
            # Check 2: an evidence line does not exist at the head sha.
            if lineno < 1 or lineno > len(text):
                errors.append(f"{tag}: line {lineno} out of range in {rel} ({len(text)} lines)")
                continue
            lines.append(text[lineno - 1])

        qtype = q.get("type", "")
        key = q.get("key")
        needs_substring = qtype in EXACT_TYPES or (
            qtype == "name_or_free" and isinstance(key, str) and " " not in key
        )
        # Check 3: key not a substring of its evidence line for exact code.
        if needs_substring:
            if not isinstance(key, str) or not key:
                errors.append(f"{tag}: exact type needs a non-empty string key")
            elif not any(key in line for line in lines):
                errors.append(f"{tag}: key {key!r} not a substring of any evidence line")

        # Check 4: q8 has no clear true or false answer.
        if qid == "q8":
            if not isinstance(key, str) or key.strip().lower() not in {"true", "false"}:
                errors.append(f"{tag}: q8 key must be 'true' or 'false', got {key!r}")
            if qtype != "bool":
                errors.append(f"{tag}: q8 type must be 'bool', got {qtype!r}")
    return errors


def check_c0(results_path: str | None) -> list[str]:
    # Check 5: the C0 score is above 60%, so the questions are too easy.
    if results_path is None:
        candidates = sorted((ROOT / "eval" / "runs").glob("*/results.json"))
        if not candidates:
            return ["check 5: no C0 results yet (run the baseline first)"]
        results_path = str(candidates[-1])
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    flags: list[str] = []
    for pr, row in sorted(data.items()):
        score = (row.get("conditions") or {}).get("c0", {}).get("correct_pct")
        if score is None:
            flags.append(f"check 5: {pr} has no C0 score in {results_path}")
        elif score > 60:
            flags.append(f"check 5: {pr} C0 {score}% above 60% — questions too easy")
    return flags


def main() -> int:
    c0_arg = sys.argv[sys.argv.index("--c0-results") + 1] if "--c0-results" in sys.argv else None
    errors: list[str] = []
    files = sorted(QUESTIONS.glob("pr*.json"))
    if len(files) != 12:
        errors.append(f"expected 12 question files, found {len(files)}")
    for path in files:
        errors.extend(validate_file(path))
    errors.extend(check_c0(c0_arg))
    blocking = [e for e in errors if not e.startswith("check 5: no C0 results yet")]
    for line in errors:
        print(line)
    if blocking:
        print(f"FAIL: {len(blocking)} blocking problem(s)")
        return 1
    print(f"PASS: {len(files)} files, checks 1-4 clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

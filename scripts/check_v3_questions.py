"""Lint, kit-validate, and citation-check Study v3 frozen questions (Phase B2).

LINT runs the parent review rules through prc.evaluation.question_lint:
option lengths stay within 25 percent of their mean with no unique
longest or shortest key, prompts name only the PR number and title, no
option echoes another study PR, no prompt asks about later changes, and
no key is the one option that echoes the most PR title words.

KIT runs the same question checks load_manifest runs, including the
decision-item rubric.

CITE checks every evidence path and symbol against the pinned
base...head diff of its own PR, for every file type the PR changes
(workflows included). With --diffs, the pinned compare JSON files are read
from that directory (named by the snapshot id after its first hyphen, for
example p1a.json); the head file is fetched only when a symbol is missing
from the patch.

Usage from the worktree root:
    .venv/bin/python scripts/check_v3_questions.py [--lint-only] [--cite-only]
        [--questions PATH] [--pairs PATH] [--diffs DIR]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from prc.evaluation import kit, question_lint

WORKTREE = Path(__file__).resolve().parents[1]
CANDIDATES = WORKTREE / "artifacts/paired-study/private/v3-candidates"

_NON_ALNUM_SPLIT = re.compile(r"[^A-Za-z0-9]+")


def load_inputs(questions_path: Path, pairs_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    questions = json.loads(questions_path.read_text())
    pairs = json.loads(pairs_path.read_text())
    meta = {}
    for pair in pairs["pairs"]:
        for snap in pair["snapshots"]:
            meta[snap["snapshot_id"]] = {
                "title": snap["title"],
                "pr_identity": snap["pr_identity"],
                "base_sha": snap["base_sha"],
                "head_sha": snap["head_sha"],
            }
    return questions, meta


def run_lint(questions: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    return question_lint.lint_study(questions, meta)


def run_kit(questions: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    snapshots = {sid: {**meta[sid], "questions": items} for sid, items in questions.items()}
    try:
        kit.validate_study_questions(snapshots)
    except kit.KitError as exc:
        return [f"kit: {exc}"]
    return []


def gh_api(*args: str) -> str:
    proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("gh api failed: " + " ".join(args) + "\n" + proc.stderr[:500])
    return proc.stdout


def compare_files(identity: str, base: str, head: str) -> list[dict[str, Any]]:
    owner_repo = identity.split("#")[0]
    raw = gh_api(f"repos/{owner_repo}/compare/{base}...{head}", "--paginate")
    data = json.loads(raw)
    pages = data if isinstance(data, list) else [data]
    files: list[dict[str, Any]] = []
    for page in pages:
        if isinstance(page, dict):
            files.extend(entry for entry in page.get("files", []) if isinstance(entry, dict))
        elif isinstance(page, list):
            files.extend(entry for entry in page if isinstance(entry, dict))
    return files


def head_text(identity: str, path: str, head: str) -> str:
    owner_repo = identity.split("#")[0]
    try:
        raw = gh_api(f"repos/{owner_repo}/contents/{path}?ref={head}", "--jq", ".content")
    except RuntimeError:
        return ""
    try:
        return base64.b64decode("".join(raw.split())).decode("utf-8", "replace")
    except ValueError:
        return ""


def evidence_items(evidence: object) -> list[dict[str, Any]]:
    if isinstance(evidence, str):
        try:
            parsed = json.loads(evidence)
        except json.JSONDecodeError:
            return []
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(evidence, list):
        return [item for item in evidence if isinstance(item, dict)]
    return []


def pinned_files(diffs: Path, sid: str) -> list[dict[str, Any]]:
    data = json.loads((diffs / f"{sid.split('-', 1)[-1]}.json").read_text())
    return [entry for entry in data.get("files", []) if isinstance(entry, dict)]


def run_cite(questions: dict[str, Any], meta: dict[str, Any], diffs: Path | None) -> list[str]:
    errors: list[str] = []
    for sid in sorted(questions):
        info = meta[sid]
        try:
            if diffs is None:
                files = compare_files(info["pr_identity"], info["base_sha"], info["head_sha"])
            else:
                files = pinned_files(diffs, sid)
        except (RuntimeError, OSError) as exc:
            errors.append(f"cite {sid}: cannot load pinned diff: {exc}")
            continue
        names = {entry.get("filename", "") for entry in files}
        patches = {entry.get("filename", ""): entry.get("patch", "") for entry in files}
        for question in questions[sid]:
            qid = str(question.get("qid", "?"))
            for item in evidence_items(question.get("evidence")):
                path = str(item.get("path", ""))
                if "#" in path or " diff on " in path:
                    errors.append(f"cite {qid}: evidence path is not a PR file: {path!r}")
                    continue
                if path not in names:
                    errors.append(f"cite {qid}: {path!r} not in the pinned diff")
                    continue
                names_cited = [
                    name
                    for name in _NON_ALNUM_SPLIT.split(str(item.get("symbol", "")))
                    if len(name) >= 3 and name not in ("com", "www")
                ]
                haystack = patches.get(path, "") or ""
                if diffs is None or any(name not in haystack for name in names_cited):
                    haystack += "\n" + head_text(info["pr_identity"], path, info["head_sha"])
                for name in names_cited:
                    if name not in haystack:
                        errors.append(f"cite {qid}: symbol {name!r} not found for {path!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lint-only", action="store_true")
    parser.add_argument("--cite-only", action="store_true")
    parser.add_argument("--questions", type=Path, default=CANDIDATES / "questions.json")
    parser.add_argument("--pairs", type=Path, default=CANDIDATES / "pairs.json")
    parser.add_argument("--diffs", type=Path, default=None)
    args = parser.parse_args()

    questions, meta = load_inputs(args.questions, args.pairs)
    failures = 0
    if not args.cite_only:
        lint_errors = run_lint(questions, meta)
        for error in lint_errors:
            print(error)
        print(f"LINT: {len(lint_errors)} error(s) over {len(questions)} snapshots")
        failures += len(lint_errors)
        kit_errors = run_kit(questions, meta)
        for error in kit_errors:
            print(error)
        print(f"KIT: {len(kit_errors)} error(s)")
        failures += len(kit_errors)
    if not args.lint_only:
        cite_errors = run_cite(questions, meta, args.diffs)
        for error in cite_errors:
            print(error)
        print(f"CITE: {len(cite_errors)} error(s)")
        failures += len(cite_errors)
    print("PASS" if failures == 0 else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

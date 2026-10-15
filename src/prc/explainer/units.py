"""Reading units: every changed piece of a pull request, so the page can explain all of it.

A unit is one changed function, method or class, the changed module lines outside
them, one step or settings block of a CI workflow, or one other changed file. Map
symbols own disjoint lines (a class owns only the lines outside its methods), so
each changed line belongs to exactly one unit. Blank lines belong to none.
"""

from __future__ import annotations

import re
from typing import Any

from prc.explainer.check import CONFIG_EXT, CONFIG_NAMES, behavior_file

Unit = dict[str, Any]
ROLES = ("code", "ci", "config", "test", "docs", "data")
DOC_EXT = (".md", ".rst", ".txt", ".adoc")
_STEP = re.compile(r"^\s+-\s+(name|uses|run):\s*(.*?)\s*$")
_JOB = re.compile(r"^  ([\w.-]+):\s*$")
_TOP = re.compile(r"^[\w-]+:")


def role(f: dict[str, Any]) -> str:
    path = str(f["path"])
    name = path.lower().rsplit("/", 1)[-1]
    if f.get("kind") == "test":
        return "test"
    if path.startswith(".github/workflows/") or name == ".gitlab-ci.yml":
        return "ci"
    if behavior_file(path):
        ext = "." + name.rsplit(".", 1)[1] if "." in name.lstrip(".") else ""
        return "config" if ext in CONFIG_EXT or name in CONFIG_NAMES else "code"
    if name.endswith(DOC_EXT) or path.lower().startswith("docs/"):
        return "docs"
    return "data"


def _changed(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ln for ln in lines if ln.get("op") in ("+", "-") and str(ln.get("text", "")).strip()]


def key(ln: dict[str, Any]) -> str:
    return ("-" + str(ln["old"])) if ln.get("op") == "-" else ("+" + str(ln["new"]))


def _unit(
    f: dict[str, Any], uid: str, kind: str, name: str, status: str, lines: list[dict[str, Any]]
) -> Unit:
    first = next((ln for ln in lines if ln.get("op") == "+"), lines[0] if lines else None)
    removed = first is not None and first.get("op") == "-"
    return {
        "id": uid,
        "path": f["path"],
        "role": role(f),
        "kind": kind,
        "name": name,
        "status": status,
        "line": None if first is None else (first["old"] if removed else first["new"]),
        "removed": removed,
        "lines": lines,
    }


def _symbol_units(f: dict[str, Any], symbols: list[dict[str, Any]]) -> list[Unit]:
    out: list[Unit] = []
    owned: set[str] = set()
    for s in symbols:
        lines = _changed([ln for h in s.get("hunks", []) for ln in h.get("lines", [])])
        owned.update(key(ln) for ln in lines)
        if not lines:
            continue
        leaf = str(s["qualname"]).rsplit(".", 1)[-1]
        kind = "test" if role(f) == "test" and leaf.startswith("test") else str(s["kind"])
        out.append(_unit(f, str(s["id"]), kind, str(s["qualname"]), str(s["status"]), lines))
    rest = [
        ln
        for ln in _changed([ln for h in f.get("hunks", []) for ln in h.get("lines", [])])
        if key(ln) not in owned
    ]
    if rest:
        out.append(_unit(f, f"{f['path']}::<module>", "module", "module level", f["status"], rest))
    return sorted(out, key=lambda u: u["line"] or 0)


def _workflow_units(f: dict[str, Any]) -> list[Unit]:
    """Split a workflow into its settings, each job's own keys, and each step."""
    blocks: dict[str, list[dict[str, Any]]] = {}
    for h in f.get("hunks", []):
        lines = h.get("lines", [])
        start = h.get("new_start") or h.get("old_start") or 0
        current, in_jobs, job = (None if start > 1 else "settings"), False, ""
        for ln in lines:
            text = str(ln.get("text", ""))
            if text.startswith("jobs:"):
                in_jobs, current = True, "settings"
            elif _TOP.match(text):
                in_jobs, current = False, "settings"
            elif in_jobs and _JOB.match(text):
                job = _JOB.match(text).group(1)  # type: ignore[union-attr]
                current = f"job {job}"
            elif (step := _STEP.match(text)) and (in_jobs or current is None or job):
                label = step.group(2).strip("'\"")
                current = f"step {label[:60]}" if label else f"step at line {ln.get('new')}"
            if current is None:
                current = f"lines from {start}"
            if ln.get("op") in ("+", "-") and text.strip():
                blocks.setdefault(current, []).append(ln)
    return [
        _unit(
            f,
            f"{f['path']}::{name}",
            "step" if name.startswith("step ") else "block",
            name,
            f["status"],
            lines,
        )
        for name, lines in blocks.items()
    ]


def units(m: dict[str, Any]) -> list[Unit]:
    """Every changed unit of the map, in diff file order."""
    by_path: dict[str, list[dict[str, Any]]] = {}
    for s in m.get("symbols", []):
        by_path.setdefault(str(s["path"]), []).append(s)
    out: list[Unit] = []
    for f in m.get("files", []):
        path = str(f["path"])
        if path in by_path:
            found = _symbol_units(f, by_path[path])
        elif role(f) == "ci" and path.endswith((".yml", ".yaml")):
            found = _workflow_units(f)
        else:
            lines = _changed([ln for h in f.get("hunks", []) for ln in h.get("lines", [])])
            found = [_unit(f, path, "file", path, str(f.get("status", "modified")), lines)]
        out += found
    return out


def listing(m: dict[str, Any]) -> str:
    """What `prc board units` prints: one row per unit, with the id a board's reading list uses."""
    rows = []
    for u in units(m):
        where = (
            (u["path"] + ":" + ("-" if u["removed"] else "") + str(u["line"]))
            if u["line"]
            else u["path"]
        )
        rows.append(
            f"{u['id']}\n    {u['role']} {u['kind']} {u['status']}, {len(u['lines'])} changed lines, {where}"
        )
    return "\n".join(rows) + "\n"

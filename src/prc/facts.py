"""Facts shared by PR summaries. Static call evidence does not prove test coverage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prc.brief import Delta, kind_of
from prc.codegraph import language_of
from prc.identity import to_jsonable

CHANGED = ("added", "modified", "deleted")
TEST_NOTE = "Static calls do not establish test coverage. The map can omit test callers."


@dataclass(frozen=True, slots=True)
class CardStats:
    files: int
    symbols_changed: int
    call_sites: int
    tests_touched: int
    ci_passed: int
    ci_total: int
    ci_text: str
    untested_total: int


@dataclass(frozen=True, slots=True)
class UntestedEntry:
    id: str
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class ParseLimit:
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class Facts:
    stats: CardStats
    no_direct_test: tuple[UntestedEntry, ...]
    test_symbol_ids: tuple[str, ...]
    limits: tuple[ParseLimit, ...]
    edges_added: int
    edges_removed: int
    ci_state: str
    test_verdict: str
    test_note: str = TEST_NOTE

    @property
    def limits_lead(self) -> str:
        if not self.limits:
            return ""
        count = "1 file" if len(self.limits) == 1 else f"{len(self.limits)} files"
        return f"Symbol and call analysis is incomplete for {count}:"


def brief_of(m: dict[str, Any], brief: Any = None) -> dict[str, Any]:
    raw = m.get("brief", {}) if brief is None else brief
    return {} if raw is None else dict(to_jsonable(raw))


def test_paths(m: dict[str, Any], brief: Any = None) -> set[str]:
    kinds = {
        f["path"]: f.get("kind", kind_of(Delta(f["path"], False, 0, 0)))
        for f in brief_of(m, brief).get("files", [])
    }
    return {
        s["path"]
        for s in m.get("symbols", [])
        if kinds.get(s["path"], kind_of(Delta(s["path"], False, 0, 0))) == "test"
    } | {path for path, kind in kinds.items() if kind == "test"}


def untested(m: dict[str, Any], brief: Any = None) -> tuple[UntestedEntry, ...]:
    tests = test_paths(m, brief)
    sources = {
        s["id"] for s in m.get("symbols", []) if s["path"] in tests and s.get("status") != "deleted"
    }
    called = {
        e["target"]
        for e in m.get("edges", [])
        if e.get("source") in sources
        and e.get("status") in ("added", "kept")
        and e.get("resolution") == "exact"
    }
    return tuple(
        sorted(
            (
                UntestedEntry(s["id"], s["qualname"], s["path"])
                for s in m.get("symbols", [])
                if s.get("status") in ("added", "modified")
                and s["path"] not in tests
                and s["id"] not in called
            ),
            key=lambda entry: entry.id,
        )
    )


def compute_facts(m: dict[str, Any], brief: Any = None) -> Facts:
    b = brief_of(m, brief)
    changed = [s for s in m.get("symbols", []) if s.get("status") in CHANGED]
    checks = b.get("checks", [])
    passed = sum(c.get("state") == "passed" for c in checks)
    missing = untested(m, b)
    tests = test_paths(m, b)
    limits = []
    for file in m.get("files", []):
        kind = kind_of(Delta(file["path"], False, 0, 0))
        if kind not in ("code", "test") or file.get("language") is not None:
            continue
        reason = (
            "not inspected"
            if file.get("kind") == "opaque"
            else "unsupported language"
            if language_of(file["path"]) is None
            else "not parsed"
        )
        limits.append(ParseLimit(file["path"], reason))
    state = (
        "none"
        if not checks
        else "failed"
        if any(c.get("state") == "failed" for c in checks)
        else "pending"
        if any(c.get("state") == "pending" for c in checks)
        else "passed"
    )
    live_prod = [
        s
        for s in m.get("symbols", [])
        if s.get("status") in ("added", "modified") and s["path"] not in tests
    ]
    deleted_prod = [
        s for s in m.get("symbols", []) if s.get("status") == "deleted" and s["path"] not in tests
    ]
    if not changed:
        verdict = (
            "No parsed symbol changes. Top-level and unrecognized changes can remain."
            if limits or any(f.get("kind") in ("code", "test") for f in b.get("files", []))
            else "No code symbols changed."
        )
    elif not live_prod:
        if deleted_prod:
            n = len(deleted_prod)
            noun = "1 production symbol deleted" if n == 1 else f"{n} production symbols deleted"
            verdict = f"{noun}. Check remaining callers for broken references."
        else:
            verdict = "No live production symbols changed."
    elif missing:
        missing_ids = {entry.id for entry in missing}
        live_ids = {s["id"] for s in live_prod}
        verdict = (
            "No direct test evidence in this map for any live changed production symbol."
            if missing_ids >= live_ids
            else "No direct test evidence in this map for some live changed production symbols."
        )
    else:
        verdict = (
            "Direct test-call evidence found for all live changed production symbols in this map."
        )
    return Facts(
        CardStats(
            len(b.get("files", [])),
            len(changed),
            sum(s.get("call_sites", 0) for s in changed),
            sum(f.get("kind") == "test" for f in b.get("files", [])),
            passed,
            len(checks),
            f"{passed}/{len(checks)}" if checks else "no CI",
            len(missing),
        ),
        missing,
        tuple(sorted(s["id"] for s in m.get("symbols", []) if s["path"] in tests)),
        tuple(sorted(limits, key=lambda entry: entry.path)),
        sum(e.get("status") == "added" for e in m.get("edges", [])),
        sum(e.get("status") == "removed" for e in m.get("edges", [])),
        state,
        verdict,
    )


def compute_stats(m: dict[str, Any], brief: Any = None) -> CardStats:
    return compute_facts(m, brief).stats

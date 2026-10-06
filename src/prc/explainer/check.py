"""Board checker: every name, value and line on screen must come from map.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

CHANGED = ("added", "modified")
ROWS = 12
VERBS: dict[str, set[str]] = {
    "title": {"claim"},
    "graph": {"show", "draw", "pulse", "focus", "walk", "flash", "note"},
    "calc": {"chip"},
    "timeline": {"bar", "ask", "overlap", "stamp", "message"},
    "groups": {"show", "tone", "fill", "strike", "fly", "mark", "note"},
    "bars": {"bars", "dim", "note"},
    "list": {"items"},
    "receipt": {"rows", "verdict"},
    "stats": {"card"},
    "outro": {"l1", "l2", "cmd"},
    "diff": {"step", "note"},
}
NEEDS = {"list": "items", "receipt": "rows"}


def spoken(scene: dict[str, Any]) -> list[str]:
    return [
        (s if isinstance(s, str) else s.get("speak", s["show"])).replace("`", "")
        for s in scene["say"]
    ]


def find_phrase(scene: dict[str, Any], phrase: str) -> list[tuple[int, int]]:
    """Every place the narration says `phrase`, as (sentence, character offset)."""
    pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
    return [
        (k, hit.start()) for k, text in enumerate(spoken(scene)) for hit in pattern.finditer(text)
    ]


def scene_ids(s: dict[str, Any]) -> set[str]:
    if s["type"] == "graph":
        return set(s["nodes"])
    if s["type"] == "groups":
        return {g["id"] for g in s["groups"]} | {it["id"] for g in s["groups"] for it in g["items"]}
    if s["type"] == "bars":
        return {b["id"] for b in s["bars"]}
    if s["type"] == "timeline":
        return {r["id"] for r in s["rows"]}
    if s["type"] == "diff":
        return {ref if isinstance(ref, str) else ref["ref"] for ref in s["lines"]}
    return set()


class Checker:
    def __init__(self, m: dict[str, Any]) -> None:
        self.sym = {s["id"]: s for s in m["symbols"]}
        self.edges = {(e["source"], e["target"]): e for e in m["edges"]}
        self.kinds = {f["path"]: f["kind"] for f in m["brief"]["files"]}
        self.head: dict[tuple[str, int], str] = {}
        self.base: dict[str, list[str]] = {}
        self.gone: dict[tuple[str, int], str] = {}
        self.order: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
        self.checks = m["brief"]["checks"]

        for f in m["files"]:
            n = 0
            for h in f["hunks"]:
                for line in h["lines"]:
                    if line["op"] != "-" and line["new"] is not None:
                        self.head[(f["path"], line["new"])] = line["text"]
                    if line["op"] != "+" and line["old"] is not None:
                        self.base.setdefault(f["path"], []).append(line["text"])
                    if line["op"] == "-":
                        self.gone[(f["path"], line["old"])] = line["text"]
                    self.order[
                        (
                            f["path"],
                            f"-{line['old']}" if line["op"] == "-" else str(line["new"]),
                        )
                    ] = (n, line)
                    n += 1
                n += 1

        self.failures: list[str] = []
        self.receipts = 0
        self.touched: set[str] = set()

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def touch(self, sid: str) -> None:
        if self.sym[sid]["status"] in CHANGED and self.kinds.get(self.sym[sid]["path"]) != "test":
            self.touched.add(sid)

    def touch_line(self, path: str, n: int) -> None:
        for s in self.sym.values():
            if s["path"] == path and s["span"] and s["span"][0] <= n <= s["span"][1]:
                self.touch(s["id"])

    def when(self, i: int, s: dict[str, Any], spec: Any) -> None:
        if isinstance(spec, str):
            n = len(find_phrase(s, spec))
            if n != 1:
                self.fail(
                    f"scene {i}: cue phrase {spec!r} is "
                    + (
                        "not in the narration"
                        if n == 0
                        else f"said {n} times in the narration; pick words said once"
                    )
                )
        elif isinstance(spec, list):
            if not (len(spec) == 2 and 0 <= spec[0] < len(s["say"]) and 0 <= spec[1] <= 1):
                self.fail(f"scene {i}: cue time {spec} is not [sentence, fraction] of this scene")
        elif not isinstance(spec, (int, float)) or spec < 0:
            self.fail(
                f"scene {i}: cue time {spec!r} is not seconds, [sentence, fraction] or a phrase"
            )

    def diff(self, i: int, s: dict[str, Any]) -> list[dict[str, Any]]:
        """Rows of a diff scene: each ref is a hunk line of the file, in diff order."""
        path: str = s["file"]
        rows: list[dict[str, Any]] = []
        last: int | None = None
        steps: set[int] = set()
        if path not in self.kinds:
            self.fail(f"scene {i}: {path} is not a file in this pull request")
            return rows
        for ref in s["lines"]:
            ref, step = (ref, None) if isinstance(ref, str) else (ref["ref"], ref.get("step"))
            self.receipts += 1
            hit = self.order.get((path, ref))
            if hit is None:
                self.fail(f"scene {i}: {path}:{ref} is not a line of the diff")
                continue
            n, line = hit
            op = line["op"] if line["op"] in ("+", "-") else " "
            if last is not None and n <= last:
                self.fail(
                    f"scene {i}: {ref} is out of diff order; list lines top to bottom as the diff shows them"
                )
            elif last is not None and n > last + 1:
                rows.append({"gap": True})
            last = n
            if op == " " and step is not None:
                self.fail(f"scene {i}: {ref} is an unchanged line, so it takes no step")
            if op == "-" and step == 0:
                self.fail(
                    f"scene {i}: {ref} is a removed line, and step 0 would hide it from the start"
                )
            step = 0 if op == " " else 1 if step is None else step
            if step:
                steps.add(step)
            if op != "-":
                self.touch_line(path, line["new"])
            num = line["old"] if op == "-" else line["new"]
            rows.append({"ref": ref, "op": op, "num": num, "text": line["text"], "step": step})
        if len(rows) > ROWS:
            self.fail(f"scene {i}: {len(rows)} rows, but the screen fits {ROWS} (gap rows count)")
        cued = {c.get("n") for c in s.get("cues", []) if c.get("do") == "step"}
        for k in sorted(steps - cued):
            self.fail(f"scene {i}: lines wait for step {k}, but no cue says when")
        for k in sorted(cued - steps, key=str):
            self.fail(f"scene {i}: the step {k} cue moves no lines")
        return rows

    def line(self, ref: str, match: str) -> str | None:
        """`path:N` is a head line; `path:-N` is base line N, which the PR removed."""
        self.receipts += 1
        path, n = ref.rsplit(":", 1)
        removed = n.startswith("-")
        got = self.gone.get((path, -int(n))) if removed else self.head.get((path, int(n)))
        needle = match.strip("…").strip()

        if got is None:
            self.fail(f"{ref}: not a {'removed' if removed else 'head'} line of the diff")
            return None
        if needle not in got:
            self.fail(f"{ref}: {needle!r} is not on that line ({got.strip()[:90]!r})")
            return None
        if removed:
            if any(needle in text for (p, _), text in self.head.items() if p == path):
                self.fail(
                    f"{ref}: {needle!r} was claimed removed, but a head line of {path} still has it"
                )
            return "code"

        self.touch_line(path, int(n))
        return "test" if self.kinds.get(path) == "test" else "code"

    def symbol(self, sid: str, status: str | None = None) -> str | None:
        self.receipts += 1
        s = self.sym.get(sid)

        if not s:
            self.fail(f"{sid}: no such symbol in the map")
            return None
        if status and s["status"] != status:
            self.fail(f"{sid}: status is {s['status']}, not {status}")
            return None

        self.touch(sid)
        return "test" if self.kinds.get(s["path"]) == "test" else "code"

    def edge(self, src: str, dst: str, status: str | None = None) -> str | None:
        self.receipts += 1
        e = self.edges.get((src, dst))

        if not e:
            self.fail(f"{src} -> {dst}: no such call in the map")
            return None
        if status and e["status"] != status:
            self.fail(f"{src} -> {dst}: status is {e['status']}, not {status}")
            return None

        self.touch(src)
        self.touch(dst)
        return "code"

    def cited_call(self, src: str, dst: str, ref: str, status: str) -> str | None:
        """A call the map missed, proven by a head line (and a base line when kept)."""
        name = self.sym[dst]["qualname"].split(".")[-1] + "("
        kind = self.line(ref, name)
        path = ref.rsplit(":", 1)[0]

        if status == "kept" and not any(name in text for text in self.base.get(path, [])):
            self.fail(f"{ref}: claimed as kept, but no base line of {path} calls {name}")

        self.symbol(src)
        self.symbol(dst)
        return kind


def tests_added(m: dict[str, Any]) -> int:
    test_paths = {f["path"] for f in m["brief"]["files"] if f["kind"] == "test"}
    return sum(
        1
        for f in m["files"]
        if f["path"] in test_paths
        for h in f["hunks"]
        for line in h["lines"]
        if line["op"] == "+"
        and re.match(r"\s*(it|test)\(\s*[\"'`]|\s*(async\s+)?def\s+test_\w*\(", line["text"])
    )


def verify_board(board: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    verdicts: dict[int, tuple[str, str]] = {}
    bar_facts: dict[str, Any] = {}
    ck = Checker(m)

    for i, s in enumerate(board["scenes"]):
        if s["type"] not in VERBS:
            ck.fail(f"scene {i}: unknown scene type {s['type']!r}")
            continue
        ids = scene_ids(s)
        pairs = (
            [e if isinstance(e, list) else [e["s"], e["t"]] for e in s.get("edges", [])]
            if s["type"] == "graph"
            else []
        )
        if s["type"] in NEEDS and not any(
            c.get("do") == NEEDS[s["type"]] for c in s.get("cues", [])
        ):
            ck.fail(f"scene {i}: a {s['type']} scene needs a {NEEDS[s['type']]!r} cue")
        for c in s.get("cues", []):
            verb = c.get("do", "claim" if "claim" in c else None)
            if verb not in VERBS[s["type"]]:
                ck.fail(f"scene {i}: unknown cue {verb!r} for a {s['type']} scene")
            ck.when(i, s, c.get("at"))
            if "until" in c:
                ck.when(i, s, c["until"])
            named = [c[k] for k in ("id", "from", "to", "line") if k in c] + [
                x for k in ("ids", "path", "keep") for x in c.get(k, [])
            ]
            for x in named:
                if x not in ids:
                    ck.fail(f"scene {i}: cue {verb!r} names no such id {x!r}")
            for e in c.get("edges", []) if s["type"] == "graph" else []:
                if list(e[:2]) not in pairs:
                    ck.fail(
                        f"scene {i}: cue {verb!r} names {e[0]} -> {e[1]}, which is not an edge of this scene"
                    )

        for c in s.get("cite", []):
            ck.line(c["line"], c["match"])

        if s["type"] == "diff":
            s["rows"] = ck.diff(i, s)

        for shown in [s.get("big", "")] + [c["value"] for c in s.get("cards", [])]:
            if re.search(r"\d", re.sub(r"\{\w+\}", "", shown)):
                ck.fail(
                    f"scene {i}: {shown!r} types a number; use a fact like {{tests_added}} so the checker computes it"
                )
            if "{items}" in shown:
                ck.fail(
                    f"scene {i}: {{items}} counts only the items this board picked, and a big number reads as a total; "
                    "use a fact about the pull request or leave big out"
                )

        if s["type"] == "graph":
            for nid in s["nodes"]:
                ck.symbol(nid)
            for e in s["edges"]:
                if isinstance(e, list):
                    ck.edge(e[0], e[1])
                else:
                    ck.cited_call(e["s"], e["t"], e["line"], e["status"])

        if s["type"] == "list":
            for item in s["items"]:
                ck.line(item["cite"], item["text"])

        if s["type"] == "bars":
            files = {f["path"]: f["added"] for f in m["brief"]["files"]}
            owner: dict[str, str] = {}
            for b in s["bars"]:
                if b.get("tone", "grey") not in (
                    "blue",
                    "green",
                    "grey",
                    "gold",
                    "red",
                    "good",
                    "bad",
                    "info",
                ):
                    ck.fail(
                        f"scene {i}: bar {b['id']!r} has tone {b['tone']!r}, which the engine cannot draw"
                    )
                b["value"] = 0
                for path, added in files.items():
                    if any(
                        path == p or (p.endswith("/") and path.startswith(p)) for p in b["paths"]
                    ):
                        if path in owner:
                            ck.fail(f"{path} is in both {owner[path]!r} and {b['id']!r}")
                        owner[path] = b["id"]
                        b["value"] += added
                ck.receipts += 1
            for path in files:
                if path not in owner:
                    ck.fail(f"{path} is in no bar, so the bars would hide it")
            total = sum(files.values())
            s["big"] = str(total)
            bar_facts.update({f"added_{b['id']}": b["value"] for b in s["bars"]}, added_total=total)

        if s["type"] == "groups":
            cited = [
                ck.head.get((c["line"].rsplit(":", 1)[0], int(c["line"].rsplit(":", 1)[1])))
                or ck.gone.get((c["line"].rsplit(":", 1)[0], -int(c["line"].rsplit(":", 1)[1])), "")
                for c in s.get("cite", [])
            ]
            for g in s["groups"]:
                for it in g["items"] + ([{"text": g["ground"]}] if "ground" in g else []):
                    word = it.get("ground", it["text"])
                    ck.receipts += 1
                    if not any(word in text for text in cited):
                        ck.fail(
                            f"scene {i}: {word!r} is on screen but on none of the scene's cited lines"
                        )

        if s["type"] == "receipt":
            kinds = set()

            for r in s["rows"]:
                if "symbol" in r:
                    kinds.add(ck.symbol(r["symbol"], r.get("status")))
                if "edge" in r:
                    kinds.add(ck.edge(r["edge"][0], r["edge"][1], r.get("status")))
                if "line" in r:
                    kinds.add(ck.line(r["line"], r.get("match", r["text"])))

            code, test = "code" in kinds, "test" in kinds

            if s.get("extra"):
                verdicts[i] = (
                    ("NOT IN THE TITLE · TESTED", "info")
                    if test
                    else ("NOT IN THE TITLE · NO TEST", "bad")
                )
            elif code and test:
                verdicts[i] = ("BACKED BY CODE + TESTS", "good")
            elif code:
                verdicts[i] = ("CODE, NO TEST", "info")
            else:
                verdicts[i] = ("NOT FOUND IN THE CODE", "bad")

    changed = {
        s["id"]
        for s in m["symbols"]
        if s["status"] in CHANGED and ck.kinds.get(s["path"]) != "test"
    }
    claims = [
        i for i, s in enumerate(board["scenes"]) if s["type"] == "receipt" and not s.get("extra")
    ]
    facts: dict[str, Any] = {
        "tests_added": tests_added(m),
        "changed": len(changed),
        "covered": len(ck.touched & changed),
        "claims": len(claims),
        "backed": sum(1 for i in claims if verdicts[i][1] == "good"),
        "checks_passed": sum(1 for c in ck.checks if c["state"] == "passed"),
        "checks_total": len(ck.checks),
        **bar_facts,
        "verdicts": verdicts,
        "receipts": ck.receipts,
    }

    for s in board["scenes"]:
        for a in s.get("assert", []):
            want = facts[a["equals_fact"]] if "equals_fact" in a else a["equals"]
            if facts[a["fact"]] != want:
                ck.fail(f"narration says {a['fact']} = {want}, the map says {facts[a['fact']]}")

    if ck.failures:
        sys.exit("receipts failed:\n  " + "\n  ".join(ck.failures))

    return facts


def main(argv: list[str]) -> int:
    board = json.loads(Path(argv[0]).read_text())
    m = json.loads(Path(argv[1]).read_text())
    facts = verify_board(board, m)
    print(f"{facts['receipts']} receipts verified")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Board checker: every name, value and line on screen must come from map.json."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from prc.explainer.preflight import (
    coverage_summary,
    join_preflight,
    line_coverage,
    note_risks,
    silent_estimate,
)
from prc.explainer.speech import speakable

CHANGED = ("added", "modified")
ROWS = 12
LABEL = 30
MAX_SECONDS = 150
CODE_EXT = frozenset(
    [
        ".py",
        ".pyi",
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".sh",
        ".bash",
        ".zsh",
        ".sql",
        ".rb",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".swift",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".cs",
        ".php",
        ".scala",
        ".lua",
        ".pl",
        ".ex",
        ".exs",
        ".dart",
        ".vue",
        ".svelte",
        ".css",
        ".scss",
        ".html",
    ]
)
CONFIG_EXT = frozenset([".toml", ".yml", ".yaml", ".ini", ".cfg", ".conf"])
CONFIG_NAMES = frozenset(
    [
        "dockerfile",
        "makefile",
        "package.json",
        "jenkinsfile",
        "procfile",
        "gemfile",
        "go.mod",
        ".env.example",
    ]
)
LOCKS = frozenset(
    [
        "uv.lock",
        "poetry.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "cargo.lock",
        "gemfile.lock",
        "go.sum",
        "composer.lock",
        "pipfile.lock",
    ]
)
NOT_BEHAVIOR_DIRS = frozenset(
    [
        "tests",
        "test",
        "__tests__",
        "docs",
        "dist",
        "build",
        "artifacts",
        "reports",
        "node_modules",
        "vendor",
    ]
)
NOT_BEHAVIOR_EXT = frozenset(
    [
        ".md",
        ".mdx",
        ".rst",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".pdf",
        ".mp4",
        ".mp3",
        ".wav",
        ".zip",
        ".gz",
        ".woff",
        ".woff2",
        ".ttf",
    ]
)
# ASD-STE100 sentence limits: an instruction tells the viewer to do something, a description states a fact.
MAX_INSTRUCTION = 20
MAX_DESCRIPTION = 25
IMPERATIVES = frozenset(
    [
        "add",
        "ask",
        "begin",
        "call",
        "check",
        "click",
        "compare",
        "consider",
        "look",
        "go",
        "keep",
        "make",
        "mind",
        "note",
        "notice",
        "open",
        "pick",
        "read",
        "remember",
        "review",
        "run",
        "see",
        "skip",
        "start",
        "stop",
        "test",
        "trust",
        "try",
        "use",
        "verify",
        "watch",
        "write",
        "never",
        "do",
        "don't",
        "focus",
        "follow",
        "find",
        "expect",
    ]
)
BE_FORMS = frozenset(
    [
        "be",
        "is",
        "are",
        "was",
        "were",
        "been",
        "being",
        "am",
        "get",
        "gets",
        "got",
        "gotten",
        "getting",
    ]
)
ADVERBS = frozenset(
    ["not", "now", "never", "also", "still", "always", "only", "then", "just", "already", "often"]
)
PARTICIPLES = frozenset(
    [
        "done",
        "made",
        "given",
        "taken",
        "shown",
        "seen",
        "known",
        "written",
        "built",
        "sent",
        "kept",
        "held",
        "run",
        "set",
        "found",
        "left",
        "lost",
        "read",
        "put",
        "cut",
        "hit",
        "brought",
        "bought",
        "caught",
        "taught",
        "thought",
        "told",
        "sold",
        "paid",
        "said",
        "spent",
        "won",
        "chosen",
        "drawn",
        "driven",
        "broken",
        "spoken",
        "stolen",
        "frozen",
        "forgotten",
        "hidden",
        "thrown",
        "grown",
        "blown",
        "flown",
        "worn",
        "torn",
        "begun",
        "struck",
        "stuck",
        "bound",
        "fed",
        "led",
        "met",
        "felt",
        "dealt",
        "meant",
        "lent",
        "bent",
        "rebuilt",
        "rewritten",
        "overridden",
        "undone",
        "split",
        "shut",
        "spread",
        "let",
        "cast",
        "forbidden",
        "withheld",
        "laid",
        "shaken",
        "eaten",
        "understood",
        "forgiven",
    ]
)
NOT_PARTICIPLES = frozenset(
    [
        "need",
        "indeed",
        "speed",
        "seed",
        "feed",
        "bed",
        "red",
        "shed",
        "bleed",
        "breed",
        "proceed",
        "succeed",
        "exceed",
        "embed",
    ]
)
_SENTENCE_END = re.compile(
    r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)[.!?]+[\"')\]]*\s+(?=[\"'(\[]*[A-Z0-9])"
)
_CODE_SPAN = re.compile(r"\x60[^\x60]*\x60")
VERBS: dict[str, set[str]] = {
    "title": {"claim"},
    "graph": {"show", "draw", "pulse", "focus", "walk", "flash", "note"},
    "calc": {"chip"},
    "timeline": {"bar", "ask", "overlap", "stamp", "message"},
    "groups": {"show", "tone", "fill", "strike", "fly", "arrow", "mark", "note"},
    "bars": {"bars", "dim", "note"},
    "list": {"items"},
    "receipt": {"rows", "verdict"},
    "stats": {"card"},
    "outro": {"l1", "l2", "cmd"},
    "diff": {"step", "note"},
}
NEEDS = {"list": "items", "receipt": "rows"}


def behavior_file(path: str) -> bool:
    """Code, CI workflows and config: the files whose change alters what the software does.

    Tests, lock files, generated or binary files, evidence and reports, and docs are not.
    """
    parts = path.lower().split("/")
    name = parts[-1]
    ext = "." + name.rsplit(".", 1)[1] if "." in name.lstrip(".") else ""
    if any(part in NOT_BEHAVIOR_DIRS for part in parts[:-1]):
        return False
    if name in LOCKS or ext == ".lock" or ext in NOT_BEHAVIOR_EXT or ".min." in name:
        return False
    if re.fullmatch(r"test_.*\.py|.*_test\.\w+|.*\.(test|spec)\.\w+", name):
        return False
    if (
        name in CONFIG_NAMES
        or name.startswith("dockerfile")
        or re.fullmatch(r"tsconfig.*\.json|requirements.*\.txt|\.env\..*example", name)
    ):
        return True
    return ext in CODE_EXT or ext in CONFIG_EXT


def shown_files(board: dict[str, Any]) -> set[str]:
    """Files a scene puts on screen: a diff scene's file, or the path of a cited line."""
    shown: set[str] = set()
    for s in board["scenes"]:
        if s["type"] == "diff":
            shown.add(s["file"])
        refs = [c.get("line") for c in s.get("cite", [])]
        refs += [it.get("cite") for it in s.get("items", []) if isinstance(it, dict)]
        refs += [r.get("line") for r in s.get("rows", []) if isinstance(r, dict)]
        refs += [e.get("line") for e in s.get("edges", []) if isinstance(e, dict)]
        shown.update(ref.rsplit(":", 1)[0] for ref in refs if isinstance(ref, str) and ":" in ref)
    return shown


def missing_behavior_files(board: dict[str, Any], m: dict[str, Any]) -> list[str]:
    """Changed behavior files no scene shows. A file with no diff line to quote is not required."""
    tests = {f["path"] for f in m["brief"]["files"] if f.get("kind") == "test"}
    shown = shown_files(board)
    return sorted(
        f["path"]
        for f in m["files"]
        if f.get("status") != "deleted"
        and f["path"] not in tests
        and behavior_file(f["path"])
        and any(h.get("lines") for h in f.get("hunks", []))
        and f["path"] not in shown
    )


def scripted(scene: dict[str, Any]) -> list[str]:
    """What each sentence gives the voice, before code names are rewritten."""
    return [
        (s if isinstance(s, str) else s.get("speak", s["show"])).replace("`", "")
        for s in scene["say"]
    ]


def spoken(scene: dict[str, Any]) -> list[str]:
    return [speakable(text) for text in scripted(scene)]


def _words(sentence: str) -> list[str]:
    """Words as a reader counts them: a code span is one word, bare punctuation is none."""
    plain = _CODE_SPAN.sub("code", sentence)
    return [w for w in plain.split() if re.search(r"\w", w)]


def _passive(words: list[str]) -> str | None:
    """The first be or get form followed, past at most one adverb, by a past participle."""
    bare = [re.sub(r"^\W+|\W+$", "", w).lower() for w in words]
    for k, word in enumerate(bare):
        if word not in BE_FORMS:
            continue
        j = k + 1
        if j < len(bare) and bare[j] in ADVERBS:
            j += 1
        if j >= len(bare):
            continue
        verb = bare[j]
        regular = verb.endswith("ed") and len(verb) > 3 and verb not in NOT_PARTICIPLES
        if regular or verb in PARTICIPLES:
            return " ".join(re.sub(r"^\W+|\W+$", "", w) for w in words[k : j + 1])
    return None


def narration_problems(i: int | str, scene: dict[str, Any]) -> list[str]:
    """ASD-STE100 rules for each caption: one short sentence in the active voice."""
    where = f"scene {i}" if isinstance(i, int) else i
    problems: list[str] = []
    for say in scene.get("say", []):
        caption = say if isinstance(say, str) else say["show"]
        parts = [p for p in _SENTENCE_END.split(_CODE_SPAN.sub("code", caption)) if p.strip()]
        if len(parts) > 1:
            problems.append(
                f"{where}: {caption!r} holds {len(parts)} sentences; ASD-STE100 asks for "
                "one statement per sentence, so give each its own say entry"
            )
        words = _words(caption)
        if not words:
            continue
        first = re.sub(r"^\W+|\W+$", "", words[0]).lower()
        if first in IMPERATIVES and len(words) > MAX_INSTRUCTION:
            problems.append(
                f"{where}: {caption!r} is an instruction of {len(words)} words; "
                f"ASD-STE100 allows {MAX_INSTRUCTION} at most"
            )
        elif first not in IMPERATIVES and len(words) > MAX_DESCRIPTION:
            problems.append(
                f"{where}: {caption!r} is a description of {len(words)} words; "
                f"ASD-STE100 allows {MAX_DESCRIPTION} at most"
            )
        phrase = _passive(words)
        if phrase:
            problems.append(
                f"{where}: {caption!r} uses the passive {phrase!r}; ASD-STE100 asks for the "
                "active voice, so name who does the action"
            )
    return problems


READING_GROUP = 4
SHARED_ROLES = ("test", "docs", "data")


def reading_problems(board: dict[str, Any], m: dict[str, Any]) -> list[str]:
    """The reading path gives every changed unit one entry: one or two plain sentences.

    Tests, docs and data may share an entry across files. Code, CI and config entries
    stay in one file and hold at most READING_GROUP units, so each function gets words.
    """
    from prc.explainer.units import units

    known = {u["id"]: u for u in units(m)}
    reading = board.get("reading")
    if not isinstance(reading, list):
        return [
            "board has no reading list; run `prc board units` and give every unit "
            "one sentence in `reading`"
        ]
    problems: list[str] = []
    seen: dict[str, int] = {}
    for k, entry in enumerate(reading):
        where = f"reading {k}"
        ids = entry.get("units") if isinstance(entry, dict) else None
        say = entry.get("say") if isinstance(entry, dict) else None
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
            problems.append(f"{where}: needs a nonempty units list of unit ids")
            continue
        sentences = [say] if isinstance(say, str) else say
        if (
            not isinstance(sentences, list)
            or not 1 <= len(sentences) <= 2
            or not all(isinstance(s, str) and s.strip() for s in sentences)
        ):
            problems.append(f"{where}: say needs one or two sentences")
        else:
            problems += narration_problems(where, {"say": sentences})
        found = []
        for uid in ids:
            if uid not in known:
                problems.append(
                    f"{where}: {uid!r} is not a unit of this pull request; run `prc board units`"
                )
            elif uid in seen:
                problems.append(f"{where}: {uid!r} is already explained in reading {seen[uid]}")
            else:
                seen[uid] = k
                found.append(known[uid])
        roles = {u["role"] for u in found}
        paths = {u["path"] for u in found}
        if len(roles) > 1:
            problems.append(
                f"{where}: mixes {', '.join(sorted(roles))} units; give each role its own entry"
            )
        elif found and found[0]["role"] not in SHARED_ROLES:
            if len(paths) > 1:
                problems.append(
                    f"{where}: joins units from {len(paths)} files; "
                    "code, CI and config entries stay in one file"
                )
            if len(found) > READING_GROUP:
                problems.append(
                    f"{where}: joins {len(found)} units; code, CI and config entries hold "
                    f"at most {READING_GROUP}"
                )
    missing = [uid for uid in known if uid not in seen]
    if missing:
        problems.append("units with no reading sentence: " + ", ".join(missing))
    return problems


def find_phrase(scene: dict[str, Any], phrase: str) -> list[tuple[int, int]]:
    """Every place the narration says `phrase`, as (sentence, character offset)."""
    pattern = re.compile(r"(?<!\w)" + re.escape(speakable(phrase)) + r"(?!\w)", re.IGNORECASE)
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

    def link(self, i: int, s: dict[str, Any], c: dict[str, Any]) -> None:
        """A fly copies one value; an arrow relates two boxes and moves nothing."""
        texts = {it["id"]: it["text"] for g in s["groups"] for it in g["items"]}
        if c["do"] == "fly":
            a, b = texts.get(c.get("from")), texts.get(c.get("to"))
            if a is not None and b is not None and a != b:
                self.fail(
                    f"scene {i}: fly from {c['from']!r} to {c['to']!r} changes the text from "
                    f"{a!r} to {b!r}, so the box renames mid-flight; "
                    'use an "arrow" cue to relate two different items'
                )
            return
        if "from" not in c or "to" not in c:
            self.fail(f"scene {i}: arrow cue needs 'from' and 'to'")
            return
        if c["from"] == c["to"]:
            self.fail(f"scene {i}: arrow cue joins {c['from']!r} to itself")
        label = c.get("label", "")
        if not isinstance(label, str) or len(label) >= LABEL:
            self.fail(f"scene {i}: arrow label {label!r} needs text under {LABEL} characters")

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
            if not (
                len(spec) == 2
                and isinstance(spec[0], int)
                and not isinstance(spec[0], bool)
                and 0 <= spec[0] < len(s["say"])
                and isinstance(spec[1], (int, float))
                and not isinstance(spec[1], bool)
                and math.isfinite(spec[1])
                and 0 <= spec[1] <= 1
            ):
                self.fail(f"scene {i}: cue time {spec} is not [sentence, fraction] of this scene")
        elif (
            not isinstance(spec, (int, float))
            or isinstance(spec, bool)
            or not math.isfinite(spec)
            or spec < 0
        ):
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
        cued = {
            c["n"]
            for c in s.get("cues", [])
            if c.get("do") == "step"
            and isinstance(c.get("n"), int)
            and not isinstance(c["n"], bool)
        }
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


def _validate_shape(board: dict[str, Any]) -> None:
    if (
        not isinstance(board, dict)
        or not isinstance(board.get("scenes"), list)
        or not board["scenes"]
    ):
        raise SystemExit("receipts failed:\nboard needs a nonempty scenes list")
    problems: list[str] = []
    collections = {
        "graph": "nodes",
        "groups": "groups",
        "bars": "bars",
        "timeline": "rows",
        "diff": "lines",
        "list": "items",
        "stats": "cards",
        "receipt": "rows",
    }
    for i, scene in enumerate(board["scenes"]):
        if not isinstance(scene, dict):
            problems.append(f"scene {i}: needs an object")
            continue
        kind = scene.get("type")
        if not isinstance(kind, str) or kind not in VERBS:
            problems.append(f"scene {i}: needs a known scene type")
            continue
        hold = scene.get("hold", 0)
        if (
            not isinstance(hold, (int, float))
            or isinstance(hold, bool)
            or not math.isfinite(hold)
            or hold < 0
        ):
            problems.append(f"scene {i}: hold needs finite nonnegative seconds")
        field = collections.get(kind)
        if field:
            items = scene.get(field)
            if not isinstance(items, list):
                problems.append(f"scene {i}: {field} needs a list")
            elif kind not in ("graph", "diff") and any(
                not isinstance(item, dict) for item in items
            ):
                problems.append(f"scene {i}: {field} needs a list of objects")
        if kind == "diff" and not isinstance(scene.get("file"), str):
            problems.append(f"scene {i}: diff needs a file path")
        if kind == "outro":
            for field in ("l1", "l2"):
                if not isinstance(scene.get(field), str):
                    problems.append(f"scene {i}: outro needs {field} text")
        say = scene.get("say", [])
        if not isinstance(say, list) or any(
            not isinstance(text, str)
            and not (
                isinstance(text, dict)
                and isinstance(text.get("show"), str)
                and isinstance(text.get("speak", text["show"]), str)
            )
            for text in say
        ):
            problems.append(f"scene {i}: say needs a list of narration text")
            say = []
        cues = scene.get("cues", [])
        if not isinstance(cues, list) or any(not isinstance(cue, dict) for cue in cues):
            problems.append(f"scene {i}: cues needs a list of objects")
            continue
        if not say and any(isinstance(cue.get("at"), (str, list)) for cue in cues):
            problems.append(f"scene {i}: cue time needs narration in say")
    if problems:
        raise SystemExit("receipts failed:\n" + "\n".join(problems))


def verify_board(board: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    _validate_shape(board)
    verdicts: dict[int, tuple[str, str]] = {}
    bar_facts: dict[str, Any] = {}
    ck = Checker(m)

    from prc.explainer.timing import scene_windows

    windows = scene_windows(board)

    for i, s in enumerate(board["scenes"]):
        if s["type"] not in VERBS:
            ck.fail(f"scene {i}: unknown scene type {s['type']!r}")
            continue
        ids = scene_ids(s)
        for problem in narration_problems(i, s):
            ck.fail(problem)
        pairs = (
            [e if isinstance(e, list) else [e["s"], e["t"]] for e in s.get("edges", [])]
            if s["type"] == "graph"
            else []
        )
        if s["type"] in NEEDS and not any(
            c.get("do") == NEEDS[s["type"]] for c in s.get("cues", [])
        ):
            ck.fail(f"scene {i}: a {s['type']} scene needs a {NEEDS[s['type']]!r} cue")
        if s["type"] == "stats":
            shown = {c.get("i") for c in s.get("cues", []) if c.get("do") == "card"}
            for index in range(len(s["cards"])):
                if index not in shown:
                    ck.fail(f"scene {i}: card {index} needs a reveal cue")
        if s["type"] == "outro":
            shown = {c.get("do") for c in s.get("cues", [])}
            for verb in ("l1", "l2", "cmd"):
                if verb not in shown:
                    ck.fail(f"scene {i}: outro needs a {verb!r} cue")
            s.setdefault("fine", "")
        for c in s.get("cues", []):
            verb = c.get("do", "claim" if "claim" in c else None)
            if verb not in VERBS[s["type"]]:
                ck.fail(f"scene {i}: unknown cue {verb!r} for a {s['type']} scene")
            if verb == "step" and (
                not isinstance(c.get("n"), int) or isinstance(c["n"], bool) or c["n"] <= 0
            ):
                ck.fail(f"scene {i}: step cue needs a positive integer n")
            ck.when(i, s, c.get("at"))
            at = c.get("at")
            if not isinstance(at, bool) and isinstance(at, (int, float)):
                start, end = windows[i]
                if float(at) > end - start + 1e-6:
                    ck.fail(
                        f"scene {i}: cue {verb!r} at {at}s is after this scene "
                        f"ends (~{end - start:.1f}s); the reveal would never show"
                    )
            if "until" in c:
                ck.when(i, s, c["until"])
            if s["type"] == "groups" and verb in ("fly", "arrow"):
                ck.link(i, s, c)
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

    for problem in join_preflight(board, m):
        ck.fail(problem)
    missing = missing_behavior_files(board, m)
    if missing:
        ck.fail(
            "behavior files on no scene: "
            + ", ".join(missing)
            + "; show each with a diff scene, a cite, a list item or a receipt line"
        )
    if "reading" in board:
        for problem in reading_problems(board, m):
            ck.fail(problem)
    estimate = silent_estimate(board)
    if estimate > MAX_SECONDS:
        ck.fail(
            f"silent estimate ~{estimate:.0f} s is over the {MAX_SECONDS} s limit; "
            "cut scenes or sentences, and spend the time on behavior files"
        )
    if ck.failures:
        sys.exit("receipts failed:\n  " + "\n  ".join(ck.failures))
    if not ck.failures:
        from prc.explainer.timing import check_stamped_cues, estimated_scene

        estimated = {
            "scenes": [estimated_scene(s, *windows[i]) for i, s in enumerate(board["scenes"])]
        }
        for problem in check_stamped_cues(estimated):
            ck.fail(problem)

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

    cov = line_coverage(board, m)
    facts["estimate_none_seconds"] = silent_estimate(board)
    facts["changed_total"] = cov["total"]
    facts["changed_shown"] = cov["shown"]
    facts["changed_missing"] = cov["missing"]
    facts["changed_known"] = cov["known"]
    facts["changed_unavailable"] = cov["unavailable"]
    facts["coverage_summary"] = coverage_summary(cov)
    facts["note_risks"] = note_risks(board, m)

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

    print(
        f"~{facts['estimate_none_seconds']:.1f} s silent (voice none); "
        f"guide target is 45-{MAX_SECONDS} s"
    )
    print(facts["coverage_summary"])
    for risk in facts["note_risks"]:
        print(f"warning: {risk}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

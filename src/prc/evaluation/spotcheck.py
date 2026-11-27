"""Judge spot-check items: each one a sentence a person can judge where it stands.

A spot-check item shows one claim from a PRC output, the PR it comes from, where it
appears (scene, box, reading entry, infographic panel), the judge's label and reason,
and links to the lines on GitHub that prove or refute it. Box titles, arrow labels and
callouts are not sentences, so sentence() frames each one as a full sentence that
names the box or arrow it belongs to.

validate() is the boundary: the notes hub refuses a spot-check file whose items lack
a PR, a place, a full sentence, or a GitHub line link, so a context-free item cannot
reach a reader.
"""

from __future__ import annotations

import json
import random
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prc.explainer.page import files_url, scene_names
from prc.explainer.units import units

_CITE = re.compile(r"^(?P<path>[^\s:;,()]+):(?P<a>-?\d+)(?:-(?P<b>\d+))?(?:\s*\(.*\))?$")
_DIFF_SCENE = re.compile(r"^(?P<path>\S+) \(diff scene lines (?P<refs>[^)]*)\)$")
_LINE_URL = re.compile(
    r"^https://github\.com/(?P<repo>[^/]+/[^/]+)/pull/(?P<n>\d+)/files#diff-[0-9a-f]{64}[LR]\d+$"
)
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class SpotcheckError(ValueError):
    """A spot-check item a person could not judge as shown."""


@dataclass(frozen=True)
class Kit:
    """One PR's judge inputs: claims, labels, the judged board, the map and the diff."""

    pr: str
    title: str
    claims: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    board: dict[str, Any]
    m: dict[str, Any]
    diff: str
    fixes: dict[str, dict[str, Any]]


def short_pr(pr: str) -> str:
    repo, number = pr.split("#")
    return f"{repo.rsplit('/', 1)[-1]} #{number}"


def diff_line(diff: str, first: int, last: int | None = None) -> tuple[str, int, bool] | None:
    """The file line behind lines first..last of a unified diff: its first changed line."""
    path, old, new = "", 0, 0
    fallback = None
    for n, raw in enumerate(diff.splitlines(), 1):
        if raw.startswith(("+++ ", "--- ")):
            name = raw[4:]
            if name != "/dev/null":
                path = name.removeprefix("b/").removeprefix("a/")
            continue
        found = _HUNK.match(raw)
        if found:
            old, new = int(found[1]), int(found[2])
            continue
        if not path or raw.startswith(("diff ", "index ", "\\")):
            continue
        op = raw[:1]
        here: tuple[str, int, bool]
        if op == "-":
            here, old = (path, old, True), old + 1
        elif op == "+":
            here, new = (path, new, False), new + 1
        else:
            here, old, new = (path, new, False), old + 1, new + 1
        if first <= n <= (last or first):
            if op in ("+", "-"):
                return here
            fallback = fallback or here
    return fallback


def _link(kit: Kit, path: str, line: int, removed: bool = False) -> dict[str, str]:
    repo, number = kit.pr.split("#")
    return {
        "text": f"{path}:{line}" + (" (old)" if removed else ""),
        "url": files_url(repo, number, path, line, removed),
    }


def _ref(kit: Kit, ref: str) -> dict[str, str] | None:
    path, _, n = ref.rpartition(":")
    if not path or not n.lstrip("-").isdigit():
        return None
    return _link(kit, path, abs(int(n)), int(n) < 0)


def _unique(links: list[dict[str, str]]) -> list[dict[str, str]]:
    return list({link["url"]: link for link in links}.values())


def _scene(kit: Kit, claim: dict[str, Any]) -> dict[str, Any] | None:
    i = claim.get("scene")
    scenes = kit.board.get("scenes", [])
    return scenes[i] if isinstance(i, int) and 0 <= i < len(scenes) else None


def evidence(kit: Kit, label: dict[str, Any], claim: dict[str, Any]) -> list[dict[str, str]]:
    """GitHub line links: the judge's cites first, then the claim's own cites, then the scene's."""
    out: list[dict[str, str]] = []
    for part in re.split(r"[;,]\s*", str(label.get("evidence", ""))):
        found = _CITE.match(part.strip())
        if not found:
            continue
        a, b = int(found["a"]), (int(found["b"]) if found["b"] else None)
        if found["path"] == "original.diff":
            hit = diff_line(kit.diff, a, b)
            if hit:
                out.append(_link(kit, *hit))
        else:
            out.append(_link(kit, found["path"], abs(a), a < 0))
    if out:
        return _unique(out)
    by_id = {u["id"]: u for u in units(kit.m)}
    for raw in claim.get("cites", []) or []:
        cite = str(raw)
        scene_cite = _DIFF_SCENE.match(cite)
        if cite in by_id and by_id[cite]["line"]:
            u = by_id[cite]
            out.append(_link(kit, u["path"], u["line"], u["removed"]))
        elif scene_cite:
            nums = [int(x) for x in re.findall(r"-?\d+", scene_cite["refs"])]
            if nums:
                out.append(_link(kit, scene_cite["path"], abs(nums[0]), nums[0] < 0))
        elif link := _ref(kit, cite):
            out.append(link)
    if out:
        return _unique(out)[:4]
    scene = _scene(kit, claim) or {}
    for g in scene.get("groups", []):
        for it in g.get("items", []):
            if "line" in it and (link := _ref(kit, str(it["line"]))):
                out.append(link)
    for c in scene.get("cite", []):
        if link := _ref(kit, str(c["line"] if isinstance(c, dict) else c)):
            out.append(link)
    return _unique(out)[:4]


def _box_text(scene: dict[str, Any], box_id: str) -> str:
    for g in scene.get("groups", []):
        if g.get("id") == box_id:
            return str(g.get("title") or box_id)
        for it in g.get("items", []):
            if it.get("id") == box_id:
                return str(it.get("text") or box_id)
    return box_id


def place(kit: Kit, claim: dict[str, Any]) -> str:
    """Where the claim appears, in words a reader can find on the page or in the video."""
    kind = str(claim.get("kind", ""))
    if kind == "reading":
        by_id = {u["id"]: u for u in units(kit.m)}
        names = [by_id[c]["name"] for c in claim.get("cites", []) if c in by_id]
        shown = ", ".join("‘" + n + "’" for n in names[:3]) or "a changed unit"
        return "Page reading path, the entry for " + shown
    if kind == "infographic":
        return "Infographic"
    i = claim.get("scene")
    if isinstance(i, int):
        if _scene(kit, claim) is None:
            total = len(kit.board.get("scenes", []))
            raise SpotcheckError(f"scene {i} out of range for board with {total} scene(s)")
        name = scene_names(kit.board)[i]
        what = {"narration": "narration", "outro": "summary line"}.get(kind, kind)
        return f"Video and page, scene {i + 1} “{name}”, {what}"
    return kind or "PRC output"


def sentence(kit: Kit, claim: dict[str, Any]) -> str:
    """The claim as a full sentence. Narration, reading and summary lines already are."""
    text = str(claim["text"]).strip()
    kind = claim.get("kind")
    scene = _scene(kit, claim) or {}
    if kind == "box title":
        for g in scene.get("groups", []):
            parts = [str(v) for v in (g.get("title"), g.get("sub")) if v]
            if " — ".join(parts) != text:
                continue
            items = [str(it["text"]) for it in g.get("items", []) if it.get("text")]
            held = (
                (" It holds " + ", ".join("“" + x + "”" for x in items[:4]) + ".") if items else ""
            )
            if len(parts) == 2:
                return f"The box “{parts[0]}” carries the note “{parts[1]}”.{held}"
            return f"A box is titled “{parts[0]}”.{held}"
        return f"A box is titled “{text}”."
    if kind == "arrow label":
        for c in scene.get("cues", []):
            if c.get("do") == "arrow" and c.get("label") == text:
                src, dst = _box_text(scene, str(c["from"])), _box_text(scene, str(c["to"]))
                return f"An arrow from “{src}” to “{dst}” carries the label “{text}”."
        return f"An arrow carries the label “{text}”."
    if kind == "callout":
        for c in scene.get("cues", []):
            box = c.get("on") or c.get("id")
            if c.get("do") == "note" and c.get("text") == text and box:
                return f"A callout on the box “{_box_text(scene, str(box))}” says “{text}”."
        return f"A callout says “{text}”."
    if kind == "scene label":
        return f"The changed lines of {scene.get('file', 'a file')} carry the title “{text}”."
    if kind == "infographic" and ": " in text:
        panel, line = text.split(": ", 1)
        return f"The infographic panel “{panel}” says “{line}”."
    if kind == "infographic":
        return f"The infographic says “{text}”."
    return text


def item(kit: Kit, n: int, label: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    reason = str(label["reason"])
    fix = kit.fixes.get(str(label["id"]))
    if fix:
        reason += f" Fixed before render. Now: “{fix['after']}”"
    return {
        "id": f"s{n}",
        "pr": kit.pr,
        "pr_title": kit.title,
        "where": place(kit, claim),
        "text": sentence(kit, claim),
        "claim": str(claim["text"]),
        "label": str(label["label"]),
        "reason": reason,
        "evidence": evidence(kit, label, claim),
    }


def build(kits: Iterable[Kit], seed: int, supported_per_pr: int = 3) -> list[dict[str, Any]]:
    """Every flagged claim plus a seeded sample of supported ones per PR, shuffled."""
    rng = random.Random(seed)
    picks: list[tuple[Kit, dict[str, Any], dict[str, Any]]] = []
    for kit in kits:
        claims = {str(c["id"]): c for c in kit.claims}
        rows: list[tuple[Kit, dict[str, Any], dict[str, Any]]] = []
        for lab in kit.labels:
            if lab["label"] == "not_a_claim":
                continue
            key = str(lab["id"])
            if key not in claims:
                raise SpotcheckError(f"label id {key!r} has no claim to judge")
            rows.append((kit, lab, claims[key]))
        picks += [r for r in rows if r[1]["label"] != "supported"]
        supported = [r for r in rows if r[1]["label"] == "supported"]
        picks += rng.sample(supported, min(supported_per_pr, len(supported)))
    rng.shuffle(picks)
    return validate([item(kit, n, lab, claim) for n, (kit, lab, claim) in enumerate(picks, 1)])


def validate(items: list[Any]) -> list[dict[str, Any]]:
    """Refuse an item a person cannot judge as shown; each error names the item and the gap."""
    problems = []
    for raw in items:
        if not isinstance(raw, dict):
            problems.append("an item is not an object")
            continue
        sid = raw.get("id", "?")
        pr = str(raw.get("pr", ""))
        if not re.fullmatch(r"[^/\s]+/[^/\s#]+#\d+", pr):
            problems.append(f"{sid}: needs pr as owner/repo#N, got {pr!r}")
        if not str(raw.get("where", "")).strip():
            problems.append(f"{sid}: needs where (scene, box, reading entry or panel)")
        text = str(raw.get("text", "")).strip()
        if len(text.split()) < 4 or not text.endswith((".", "”", "?", "!")):
            problems.append(
                f"{sid}: text {text!r} is a label, not a sentence;"
                " frame it with prc.evaluation.spotcheck.sentence()"
            )
        links = raw.get("evidence") or []
        if isinstance(links, list) and links:
            for ev in links:
                if not isinstance(ev, dict):
                    problems.append(f"{sid}: evidence {ev!r} is not a line of {pr} on GitHub")
                    continue
                found = _LINE_URL.match(str(ev.get("url", "")))
                if not found or f"{found['repo']}#{found['n']}" != pr:
                    problems.append(
                        f"{sid}: evidence {ev.get('text')!r} is not a line of {pr} on GitHub"
                    )
                if "original.diff" in str(ev.get("text", "")):
                    problems.append(
                        f"{sid}: evidence cites original.diff; map it with"
                        " prc.evaluation.spotcheck.diff_line()"
                    )
        else:
            problems.append(f"{sid}: needs at least one GitHub line link in evidence")
    if problems:
        raise SpotcheckError("spot-check items a person cannot judge:\n" + "\n".join(problems))
    return items


def load_kit(judge_dir: Path, board_dir: Path, prepared_dir: Path, title: str) -> Kit:
    pr = json.loads((judge_dir / "pr.json").read_text())["pr_identity"]
    fixes_path = board_dir / "judge-fixes.json"
    fixes = json.loads(fixes_path.read_text()) if fixes_path.is_file() else []
    return Kit(
        pr=pr,
        title=title,
        claims=json.loads((judge_dir / "claims-A.json").read_text()),
        labels=json.loads((judge_dir / "labels-A.json").read_text()),
        board=json.loads((judge_dir / "board-A.json").read_text()),
        m=json.loads((prepared_dir / "map.json").read_text()),
        diff=(judge_dir / "original.diff").read_text(),
        fixes={str(f["claim"]): f for f in fixes},
    )

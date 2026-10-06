"""Diff-row port: pairing rules, wrap invariants and the join gate inputs."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import prc.explainer.highlight as H
from prc.explainer.check import verify_board
from prc.explainer.diffrows import pair_rows, wrap_row

DATA = Path(__file__).resolve().parent / "data" / "explainer"
BOARDS = ["mdp12", "mdp14", "mdp17b", "mdp4", "mdp4.writer", "mdp4high", "mdp4zoom"]
BOARD_MAP = {
    "mdp12": "pr12",
    "mdp14": "pr14",
    "mdp17b": "pr17",
    "mdp4": "pr4",
    "mdp4.writer": "pr4",
    "mdp4high": "pr4",
    "mdp4zoom": "pr4",
}
INVITATION = "src/linkedin_mdp_mcp/invitation_shortlist.py"


def blob_bytes(pr: str, side: str, path: str) -> bytes:
    return (DATA / "blobs" / pr / side / path).read_bytes()


def tok(text: str) -> Any:
    return H.row_tokens([(text, "")], 0)


def make_row(ref: str, op: str, step: int, text: str) -> dict[str, Any]:
    return {"ref": ref, "op": op, "step": step, "num": 1, "text": text, "tokens": tok(text)}


def chg_texts(r: dict[str, Any]) -> list[str]:
    return [str(t["text"]) for t in r["tokens"] if t.get("chg")]


def mdp17b_rows() -> list[dict[str, Any]]:
    m = json.loads((DATA / "maps" / "pr17.json").read_text())
    f = next(x for x in m["files"] if x["path"].endswith("invitation_shortlist.py"))
    by = {}
    for h in f["hunks"]:
        for ln in h["lines"]:
            by[f"-{ln['old']}" if ln["op"] == "-" else str(ln["new"])] = ln
    specs = [
        ("1030", " ", 0),
        ("-1018", "-", 1),
        ("1031", "+", 1),
        ("1032", " ", 0),
        ("1033", " ", 0),
        ("-1021", "-", 2),
        ("1034", "+", 2),
        ("1035", "+", 2),
    ]
    rows = []
    for ref, op, step in specs:
        ln = by[ref]
        rows.append(
            {
                "ref": ref,
                "op": op,
                "step": step,
                "num": ln["old"] if op == "-" else ln["new"],
                "text": ln["text"].expandtabs(4).rstrip(),
            }
        )
    head = blob_bytes("pr17", "head", INVITATION)
    base = blob_bytes("pr17", "base", INVITATION)

    def read(side: str, path: str) -> bytes:
        return base if side == "old" else head

    H.attach_tokens(
        rows, INVITATION, 0, "unused-git-dir", m["head_sha"], m["base_sha"], f["hunks"], reader=read
    )
    return rows


def test_mdp17b_pairs() -> None:
    rows = mdp17b_rows()
    pair_rows(rows)
    by = {r["ref"]: r for r in rows}
    assert by["-1018"]["pair"] == "1031"
    assert by["1031"]["pair"] == "-1018"
    assert by["-1021"]["pair"] == "1035"
    assert by["1035"]["pair"] == "-1021"
    assert "pair" not in by["1034"]


def test_gap_blocks_pairing() -> None:
    rows: list[dict[str, Any]] = [
        make_row("-5", "-", 1, "x = compute(a)"),
        {"gap": True},
        make_row("6", "+", 1, "x = compute(b)"),
    ]
    pair_rows(rows)
    assert "pair" not in rows[0] and "pair" not in rows[2]


def test_steps_differ_never_pair() -> None:
    rows = [make_row("-5", "-", 1, "x = compute(a)"), make_row("6", "+", 2, "x = compute(b)")]
    pair_rows(rows)
    assert "pair" not in rows[0] and "pair" not in rows[1]


def test_pair_below_threshold_stays_unpaired() -> None:
    rows = [
        make_row("-5", "-", 1, "aaaaaaaaaaaaaaaaaaaaaaaa"),
        make_row("6", "+", 1, "bbbbbbbbbbbbbbbbbbbbbbbb"),
    ]
    pair_rows(rows)
    assert "pair" not in rows[0] and "pair" not in rows[1]


def test_two_removed_one_added_pairs_in_order() -> None:
    rows = [
        make_row("-5", "-", 1, "import os"),
        make_row("-6", "-", 1, "x = compute(a)"),
        make_row("7", "+", 1, "x = compute(b)"),
    ]
    pair_rows(rows)
    assert "pair" not in rows[0]
    assert rows[1]["pair"] == "7" and rows[2]["pair"] == "-6"


def test_whitespace_needs_two_changed_neighbours() -> None:
    rows = [make_row("-5", "-", 1, "x = f(a)"), make_row("6", "+", 1, "x = g(a)")]
    pair_rows(rows)
    assert rows[0]["pair"] == "6"
    assert not any(
        t.get("chg") and not t["text"].strip() for t in rows[0]["tokens"] + rows[1]["tokens"]
    )
    rows = [make_row("-5", "-", 1, "p aa bb q"), make_row("6", "+", 1, "p cc dd q")]
    pair_rows(rows)
    assert rows[0]["pair"] == "6"
    got = [(t["text"], bool(t.get("chg"))) for t in rows[0]["tokens"]]
    assert got == [
        ("p", False),
        (" ", False),
        ("aa", True),
        (" ", True),
        ("bb", True),
        (" ", False),
        ("q", False),
    ]


def test_exact_changed_tokens() -> None:
    rows = mdp17b_rows()
    pair_rows(rows)
    by = {r["ref"]: r for r in rows}
    assert [t for t in chg_texts(by["-1018"]) if t.strip()] == ["candidate_row", "."]
    assert [t for t in chg_texts(by["1031"]) if t.strip()] == [
        "any",
        "(",
        "for",
        "company_id",
        "in",
        "employers",
        "[",
        "candidate_row",
        ".",
        "profile_url",
        "]",
        ".",
        "assignments",
        ")",
    ]


def test_pairing_changes_no_token_text() -> None:
    rows = mdp17b_rows()
    before = ["".join(t["text"] for t in r["tokens"]) for r in rows]
    pair_rows(rows)
    after = ["".join(t["text"] for t in r["tokens"]) for r in rows]
    assert before == after == [r["text"] for r in rows]


def cwidth(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def scene_texts(board_name: str) -> list[list[tuple[str, str]]]:
    board = json.loads((DATA / "boards" / f"{board_name}.json").read_text())
    verify_board(board, json.loads((DATA / "maps" / f"{BOARD_MAP[board_name]}.json").read_text()))
    out = []
    for s in board["scenes"]:
        if s["type"] != "diff":
            continue
        code = [r for r in s["rows"] if "text" in r]
        for r in code:
            r["text"] = r["text"].expandtabs(4).rstrip()
        cut = min(
            (len(r["text"]) - len(r["text"].lstrip()) for r in code if r["text"].strip()), default=0
        )
        out.append([(r["ref"], r["text"][cut:]) for r in code])
    return out


def wrapped(text: str, cols: int = 72) -> tuple[list[dict[str, Any]], int, list[int]]:
    toks = H.row_tokens([(text, "")], 0)
    hang, breaks = wrap_row(toks, cols)
    return toks, hang, breaks


def visual_lines(toks: list[dict[str, Any]], breaks: list[int]) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    br = set(breaks)
    for i, t in enumerate(toks):
        if i in br:
            lines.append(cur)
            cur = []
        cur.append(t)
    lines.append(cur)
    return lines


def test_wrapped_rows_join() -> None:
    n = 0
    for name in BOARDS:
        for scene in scene_texts(name):
            for ref, text in scene:
                toks, hang, _ = wrapped(text)
                assert "".join(t["text"] for t in toks) == text, (name, ref)
                assert 0 < hang <= 36, (name, ref, hang)
                n += 1
    toks, _, _ = wrapped('    x = "' + "a" * 150 + '"')
    assert "".join(t["text"] for t in toks) == '    x = "' + "a" * 150 + '"'
    assert n > 0


def test_no_visual_line_over_cols() -> None:
    for name in BOARDS:
        for scene in scene_texts(name):
            for ref, text in scene:
                toks, _, breaks = wrapped(text)
                for line in visual_lines(toks, breaks):
                    w = cwidth("".join(t["text"] for t in line))
                    assert w <= 72 or len(line) == 1, (name, ref, w)


def test_short_rows_stay_one_line() -> None:
    n = 0
    for name in BOARDS:
        for scene in scene_texts(name):
            for ref, text in scene:
                if cwidth(text) <= 72:
                    _, _, breaks = wrapped(text)
                    assert breaks == [], (name, ref, text)
                    n += 1
    assert n > 0


def test_no_whitespace_continuation() -> None:
    n = 0
    for name in BOARDS:
        for scene in scene_texts(name):
            for ref, text in scene:
                toks, _, breaks = wrapped(text)
                for b in breaks:
                    assert toks[b]["text"].strip(), (name, ref, b)
                    n += 1
    toks, _, breaks = wrapped('    x = "' + "a" * 150 + '"')
    for b in breaks:
        assert toks[b]["text"].strip()
    assert n >= 0

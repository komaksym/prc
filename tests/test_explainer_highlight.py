"""Highlighter port: the 14 Stage 2 failure modes, reading vendored blobs, never git."""

from __future__ import annotations

import contextlib
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import prc.explainer.highlight as H

DATA = Path(__file__).resolve().parent / "data" / "explainer"
MAPS = ["pr12", "pr17", "pr4", "pr14"]


def manifest() -> Any:
    return json.loads((DATA / "blobs" / "manifest.json").read_text())


def blob_reader(pr: str) -> Callable[[str, str], bytes]:
    def read(side: str, path: str) -> bytes:
        p = DATA / "blobs" / pr / ({"new": "head", "old": "base"}[side]) / path
        if not p.exists():
            raise RuntimeError(f"highlight: git show failed for {path} at <stored-sha>")
        return p.read_bytes()

    return read


def test_real_lines_join() -> None:
    skipped = manifest()
    total = bad = 0
    for pr in MAPS:
        m = json.loads((DATA / "maps" / f"{pr}.json").read_text())
        read = blob_reader(pr)
        for f in m["files"]:
            if not f["hunks"]:
                continue
            for which in ("new", "old"):
                try:
                    data = read(which, f["path"])
                except RuntimeError:
                    assert [f["path"], which] in [
                        [p, {"head": "new", "base": "old"}[s]] for p, s in skipped[pr]["skipped"]
                    ], (pr, f["path"], which)
                    continue
                assert [f["path"], which] in [
                    [p, {"head": "new", "base": "old"}[s]]
                    for p, s in skipped[pr].get("exported", [])
                ], (pr, f["path"])
                lines = H.file_runs(f["path"], data)
                for h in f["hunks"]:
                    for ln in h["lines"]:
                        num = ln["new"] if which == "new" and ln["op"] != "-" else ln["old"]
                        if (which == "new") != (ln["op"] != "-"):
                            continue
                        total += 1
                        joined = (
                            "".join(t for t, _ in lines[num - 1]) if 0 < num <= len(lines) else None
                        )
                        assert joined == ln["text"], (pr, f["path"], ln["op"], num)
    assert total > 0
    assert bad == 0


def test_multibyte_offsets() -> None:
    data = "# café 🎉 漢字\nx = 1\n".encode()
    lines = H.file_runs("m.py", data)
    assert "".join(t for t, _ in lines[0]) == "# café 🎉 漢字"
    assert "".join(t for t, _ in lines[1]) == "x = 1"
    toks = H.row_tokens(lines[0], 0)
    assert "".join(t["text"] for t in toks) == "# café 🎉 漢字"
    assert toks[0] == {"text": "#", "cls": "c"}


def test_crlf() -> None:
    lines = H.file_runs("c.py", b"x = 1\r\n\r\ny = 2\r\n")
    assert ["".join(t for t, _ in line) for line in lines] == ["x = 1", "", "y = 2"]
    assert not any("\r" in t for line in lines for t, _ in line)
    toks = H.row_tokens(lines[0], 0)
    assert not any("\r" in t["text"] for t in toks)


def test_tabs() -> None:
    assert "".join(t["text"] for t in H.row_tokens([("a\tb", "")], 0)) == "a\tb".expandtabs(4)
    assert "".join(t["text"] for t in H.row_tokens([("ab\tc", "")], 0)) == "ab\tc".expandtabs(4)
    assert "".join(t["text"] for t in H.row_tokens([("a", ""), ("\tb", "")], 0)) == "a   b"


def test_trailing_ws() -> None:
    toks = H.row_tokens([("v = 1 \t ", "")], 0)
    assert "".join(t["text"] for t in toks) == "v = 1"


def test_formfeed() -> None:
    text = "a = 1\n\x0cb = 2\n"
    lines = H.file_runs("f.py", text.encode())
    assert len(lines) == len(text.splitlines()) == 3
    assert ["".join(t for t, _ in line) for line in lines] == text.splitlines()


def test_missing_file() -> None:
    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    skipped = manifest()["pr12"]["skipped"]
    added = next(path for path, side in skipped if side == "base")
    read = blob_reader("pr12")
    with pytest.raises(RuntimeError, match="git show failed"):
        H.attach_tokens(
            [{"ref": "-1", "op": "-", "step": 1, "num": 1, "text": "x = 1"}],
            added,
            0,
            "unused-git-dir",
            m["head_sha"],
            m["base_sha"],
            [],
            reader=read,
        )
    plus = [{"ref": "1", "op": "+", "step": 1, "num": 1, "text": "x = 1"}]
    H.attach_tokens(plus, added, 0, "unused-git-dir", m["head_sha"], "0" * 40, [], reader=read)
    assert plus[0]["tokens"]
    real = next(
        f["path"]
        for f in m["files"]
        if f["hunks"] and (DATA / "blobs" / "pr12" / "head" / f["path"]).exists()
    )
    plus = [{"ref": "1", "op": "+", "step": 1, "num": 1, "text": "x = 1"}]
    H.attach_tokens(plus, real, 0, "unused-git-dir", m["head_sha"], "0" * 40, [], reader=read)
    assert plus[0]["tokens"]


def test_unknown_extension() -> None:
    assert H.file_runs("f.zzzunknown9", b"x = 1\n") == [[("x = 1", "")]]


def test_syntax_error() -> None:
    lines = H.file_runs("b.py", b"def broken(:\n    x = \n")
    assert ["".join(t for t, _ in line) for line in lines] == ["def broken(:", "    x = "]


def test_big_or_binary() -> None:
    lines = H.file_runs("big.py", b"pass\n" * 200000)
    assert len(lines) == 200000 and all(c == "" for line in lines[:1000] for _, c in line)
    lines = H.file_runs("b.py", b"x = 1\n\x00\x01\x02\nfoo\n")
    assert all(c == "" for line in lines for _, c in line)
    assert ["".join(t for t, _ in line) for line in lines] == ["x = 1", "\x00\x01\x02", "foo"]


def test_hunk_only() -> None:
    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    f = next(x for x in m["files"] if x["path"].endswith("invitation_shortlist.py"))
    rows: list[dict[str, Any]] = [{"gap": True}]
    for h in f["hunks"][:1]:
        for ln in h["lines"]:
            if ln["op"] == "-":
                rows.append(
                    {
                        "ref": f"-{ln['old']}",
                        "op": "-",
                        "step": 1,
                        "num": ln["old"],
                        "text": ln["text"].expandtabs(4).rstrip(),
                    }
                )
            else:
                rows.append(
                    {
                        "ref": str(ln["new"]),
                        "op": ln["op"],
                        "step": 0 if ln["op"] == " " else 1,
                        "num": ln["new"],
                        "text": ln["text"].expandtabs(4).rstrip(),
                    }
                )
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        H.attach_tokens(rows, f["path"], 0, None, m["head_sha"], m["base_sha"], f["hunks"][:1])
    assert out.getvalue() == ""
    assert "hunk" in err.getvalue().lower()
    for r in rows:
        if r.get("gap"):
            assert "tokens" not in r
        else:
            assert "".join(t["text"] for t in r["tokens"]) == r["text"]


def test_cut_nonspace_raises() -> None:
    for runs, cut in [([("ab", "")], 1), ([("   ab", "")], 4), ([("  x", "")], 3)]:
        with pytest.raises(ValueError):
            H.row_tokens(runs, cut)
    assert H.row_tokens([("ab", "")], 0) == [{"text": "ab", "cls": ""}]
    assert H.row_tokens([("    ", "")], 2) == []


def clsmap(path: str, data: bytes, n: int) -> tuple[list[dict[str, object]], dict[str, set[str]]]:
    toks = H.row_tokens(H.file_runs(path, data)[n - 1], 0)
    d: dict[str, set[str]] = {}
    for t in toks:
        d.setdefault(str(t["text"]), set()).add(str(t["cls"]))
    return toks, d


def test_colours() -> None:
    data = (
        DATA / "blobs" / "pr12" / "head" / "src/linkedin_mdp_mcp/invitation_shortlist.py"
    ).read_bytes()
    _, d = clsmap("invitation_shortlist.py", data, 453)
    assert d.get("if") == {"k"}
    assert d.get("len") == {"f"}
    assert d.get("!") == {"k"} and d.get("=") == {"k"}
    assert d.get("1") == {"n"}
    _, d = clsmap("invitation_shortlist.py", data, 1031)
    assert d.get("update") == {"f"}
    assert d.get("_date_added") == {"f"}
    _, d = clsmap("invitation_shortlist.py", data, 473)
    assert d.get("reason") == {"s"}
    _, d = clsmap("invitation_shortlist.py", data, 474)
    assert d.get("None") == {"k"}
    toks, _ = clsmap("n.py", b"# note\n", 1)
    assert toks and all(t["cls"] == "c" for t in toks)
    _, d = clsmap("f.js", b"const f = () => 1\n", 1)
    assert d.get("const") == {"k"}
    assert d.get("=") == {"k"} and d.get(">") == {"k"}
    _, d = clsmap("a.ts", b"type A = {a: number}\n", 1)
    assert d.get("type") == {"k"}
    _, d = clsmap("x.rs", b"fn main() {\n    // hi\n}\n", 2)
    assert d.get("hi") == {"c"}
    _, d = clsmap("x.rs", b"fn main() {\n    // hi\n}\n", 1)
    assert d.get("fn") == {"k"}


def test_blank_row() -> None:
    assert H.row_tokens([], 3) == []
    assert H.row_tokens([], 0) == []
    assert "".join(t["text"] for t in H.row_tokens([], 3)) == ""

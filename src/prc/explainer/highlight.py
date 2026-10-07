"""Whole-file syntax highlighting to per-row tokens. Join-tested: tokens join to the diff line."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import tree_sitter_javascript as tj
import tree_sitter_python as tp
import tree_sitter_typescript as tt
from tree_sitter import Language, Parser, Query, QueryCursor

_TSQ_PATH = os.path.join(os.path.dirname(tt.__file__), "queries", "highlights.scm")
_TSQ = Path(_TSQ_PATH).read_text()
GRAMMARS = {
    ".py": (tp.language, tp.HIGHLIGHTS_QUERY),
    ".pyi": (tp.language, tp.HIGHLIGHTS_QUERY),
    ".js": (tj.language, tj.HIGHLIGHTS_QUERY),
    ".jsx": (tj.language, tj.HIGHLIGHTS_QUERY),
    ".mjs": (tj.language, tj.HIGHLIGHTS_QUERY),
    ".cjs": (tj.language, tj.HIGHLIGHTS_QUERY),
    ".ts": (tt.language_typescript, tj.HIGHLIGHTS_QUERY + _TSQ),
    ".mts": (tt.language_typescript, tj.HIGHLIGHTS_QUERY + _TSQ),
    ".cts": (tt.language_typescript, tj.HIGHLIGHTS_QUERY + _TSQ),
    ".tsx": (tt.language_tsx, tj.HIGHLIGHTS_QUERY + _TSQ),
}
CLASS = [
    ("comment", "c"),
    ("string", "s"),
    ("escape", "s"),
    ("number", "n"),
    ("keyword", "k"),
    ("operator", "k"),
    ("constant.builtin", "k"),
    ("variable.builtin", "k"),
    ("function", "f"),
]

SKIP_BYTES = 512 * 1024


def cls_of(name: str) -> str:
    return next((c for p, c in CLASS if name == p or name.startswith(p + ".")), "")


def classes_ts(ext: str, data: bytes) -> list[str]:
    g, q = GRAMMARS[ext]
    lang = Language(g())
    tree = Parser(lang).parse(data)
    paint = []
    for pat, caps in QueryCursor(Query(lang, q)).matches(tree.root_node):
        for name, nodes in caps.items():
            for n in nodes:
                c = cls_of(name)
                paint.append(
                    (-(n.end_byte - n.start_byte), bool(c), -pat, n.start_byte, n.end_byte, c)
                )
    out = [""] * len(data)
    for *_, a, b, c in sorted(paint):
        out[a:b] = [c] * (b - a)
    return out


def classes_pyg(path: str, data: bytes) -> list[str]:
    from pygments.lexers import get_lexer_for_filename  # type: ignore[import-untyped]  # noqa: I001
    from pygments.token import (  # type: ignore[import-untyped]  # noqa: I001
        Comment,
        Keyword,
        Name,
        Number,
        Operator,
        String,
    )

    try:
        lexer = get_lexer_for_filename(path, stripnl=False, stripall=False, ensurenl=False)
    except Exception:
        return [""] * len(data)
    m = [
        (Comment, "c"),
        (String, "s"),
        (Number, "n"),
        (Keyword, "k"),
        (Operator, "k"),
        (Name.Builtin, "f"),
        (Name.Function, "f"),
    ]
    out = []
    for tok, val in lexer.get_tokens(data.decode()):
        out += [next((c for t, c in m if tok in t), "")] * len(val.encode())
    return out


def file_runs(path: str, data: bytes) -> list[list[tuple[str, Any]]]:
    """Line N (1-based, str.splitlines numbering like the map) -> [(text, cls)] runs."""
    text = data.decode("utf-8", "replace")
    data = text.encode()
    if len(data) > SKIP_BYTES or b"\x00" in data[:8192]:
        return [[(line, "")] if line else [] for line in text.splitlines()]
    ext = os.path.splitext(path)[1]
    cls = classes_ts(ext, data) if ext in GRAMMARS else classes_pyg(path, data)
    lines: list[list[tuple[str, Any]]] = []
    at = 0
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\r\n\x0b\x0c\x1c\x1d\x1e\x85  ")
        b = len(body.encode())
        runs: list[tuple[str, Any]] = []
        cur: Any = None
        start = at
        for i in range(at, at + b):
            if cls[i] != cur:
                if i > start:
                    runs.append((data[start:i].decode(), cur))
                cur, start = cls[i], i
        if at + b > start:
            runs.append((data[start : at + b].decode(), cur))
        lines.append(runs)
        at += len(raw.encode())
    return lines


def split(runs: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Runs -> tokens: words, single punctuation, whitespace runs; each keeps its class."""
    return [(t, c) for text, c in runs for t in re.findall(r"\s+|\w+|[^\w\s]", text)]


def row_tokens(runs: list[tuple[str, Any]], cut: int) -> list[dict[str, Any]]:
    """Runs of one line -> [{text, cls}] after expandtabs(4), rstrip, and the common-indent cut."""
    col = 0
    expanded: list[list[Any]] = []
    for text, c in runs:
        s = []
        for ch in text:
            if ch == "\t":
                n = 4 - (col % 4)
                s.append(" " * n)
                col += n
            else:
                s.append(ch)
                col += 1
        expanded.append(["".join(s), c])
    for i in range(len(expanded) - 1, -1, -1):
        expanded[i][0] = re.sub(r"\s+$", "", expanded[i][0])
        if expanded[i][0]:
            break
    toks = [
        {"text": t, "cls": c}
        for text, c in expanded
        if text
        for t in re.findall(r"\s+|\w+|[^\w\s]", text)
    ]
    if cut:
        if not toks:
            return []
        left: int = cut
        res: list[dict[str, Any]] = []
        for t in toks:
            if left <= 0:
                res.append(t)
                continue
            if left >= len(t["text"]):
                if t["text"].strip():
                    raise ValueError(f"highlight: cut {cut} hits non-space in {t['text']!r}")
                left -= len(t["text"])
                continue
            if t["text"][:left].strip():
                raise ValueError(f"highlight: cut {cut} hits non-space in {t['text']!r}")
            res.append({"text": t["text"][left:], "cls": t["cls"]})
            left = 0
        if left:
            raise ValueError("highlight: row shorter than cut")
        toks = [t for t in res if t["text"]]
    return toks


def _git_reader(git_dir: str, head_sha: str, base_sha: str) -> Callable[[str, str], bytes]:
    def read(side: str, path: str) -> bytes:
        sha = head_sha if side == "new" else base_sha
        r = subprocess.run(
            ["git", "--git-dir", git_dir, "show", f"{sha}:{path}"], capture_output=True
        )
        if r.returncode != 0:
            raise RuntimeError(
                f"highlight: git show failed for {path} at {sha[:7]}: {r.stderr.decode().strip()}"
            )
        return r.stdout

    return read


def attach_tokens(
    rows: list[dict[str, Any]],
    path: str,
    cut: int,
    git_dir: str | None,
    head_sha: str,
    base_sha: str,
    hunks: list[dict[str, Any]],
    reader: Callable[[str, str], bytes] | None = None,
) -> None:
    """Set tokens on every code row. Reads whole files from git, or hunk text without git_dir."""
    cache: dict[str, Any] = {}

    def side_runs(side: str) -> dict[int, list[tuple[str, Any]]]:
        if side in cache:
            return cache[side]  # type: ignore[no-any-return]
        read = reader or _git_reader(git_dir or "", head_sha, base_sha)
        if git_dir or reader is not None:
            by_num = {i + 1: line for i, line in enumerate(file_runs(path, read(side, path)))}
        else:
            if "warned" not in cache:
                print(
                    f"warning: highlighting {path} from hunk text only; "
                    "colours may be wrong at hunk edges",
                    file=sys.stderr,
                )
                cache["warned"] = True
            if side == "new":
                sel = [
                    (line["new"], line["text"])
                    for h in hunks
                    for line in h["lines"]
                    if line["op"] != "-"
                ]
            else:
                sel = [
                    (line["old"], line["text"])
                    for h in hunks
                    for line in h["lines"]
                    if line["op"] != "+"
                ]
            lines = file_runs(path, "\n".join(t for _, t in sel).encode())
            by_num = {n: lines[i] for i, (n, _) in enumerate(sel)}
        cache[side] = by_num
        return by_num

    for r in rows:
        if r.get("gap"):
            continue
        side = "old" if r.get("op") == "-" else "new"
        runs = side_runs(side).get(r["num"])
        if runs is None:
            raise RuntimeError(f"highlight: {path} has no line {r['num']} for row {r.get('ref')}")
        r["tokens"] = row_tokens(runs, cut)

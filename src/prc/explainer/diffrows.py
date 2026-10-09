"""Diff-row post-processing: pair replaced lines, flag changed tokens, soft-wrap rows."""

from __future__ import annotations

import itertools
import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

MIN_RATIO = 0.4
DIFF_BOTTOM = 862


def prepare(rows: list[dict[str, Any]]) -> int:
    """Expand tabs, trim trailing space and remove the common indent."""
    code = [r for r in rows if "text" in r]
    for r in code:
        r["text"] = r["text"].expandtabs(4).rstrip()
    cut = min(
        (len(r["text"]) - len(r["text"].lstrip()) for r in code if r["text"].strip()),
        default=0,
    )
    for r in code:
        r["text"] = r["text"][cut:]
    return cut


def _words(tokens: list[dict[str, Any]]) -> list[int]:
    return [i for i, t in enumerate(tokens) if t["text"].strip()]


def _ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    return SequenceMatcher(
        None,
        [a["tokens"][i]["text"] for i in _words(a["tokens"])],
        [b["tokens"][i]["text"] for i in _words(b["tokens"])],
        autojunk=False,
    ).ratio()


def _blocks(
    rows: list[dict[str, Any]],
) -> Any:
    """Runs of removed rows followed directly by added rows of the same step (no gap row between)."""
    i = 0
    while i < len(rows):
        if rows[i].get("op") != "-":
            i += 1
            continue
        j = i
        while j < len(rows) and rows[j].get("op") == "-" and rows[j]["step"] == rows[i]["step"]:
            j += 1
        k = j
        while k < len(rows) and rows[k].get("op") == "+" and rows[k]["step"] == rows[i]["step"]:
            k += 1
        yield rows[i:j], rows[j:k]
        i = max(k, i + 1)


def pair_rows(rows: list[dict[str, Any]]) -> None:
    """Set r['pair'] (partner ref) and chg flags on changed tokens of paired rows."""
    for old, new in _blocks(rows):
        start = 0
        for o in old:
            best = max(
                ((_ratio(o, n), j) for j, n in enumerate(new) if j >= start), default=(0, -1)
            )
            if best[0] < MIN_RATIO:
                continue
            n = new[best[1]]
            start = best[1] + 1
            o["pair"], n["pair"] = n["ref"], o["ref"]
            for r in (o, n):
                other = n if r is o else o
                ao, bo = _words(r["tokens"]), _words(other["tokens"])
                sm = SequenceMatcher(
                    None,
                    [r["tokens"][i]["text"] for i in ao],
                    [other["tokens"][i]["text"] for i in bo],
                    autojunk=False,
                )
                mark = [False] * len(r["tokens"])
                for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
                    if tag != "equal":
                        for i in ao[i1:i2]:
                            mark[i] = True
                for i, t in enumerate(r["tokens"]):
                    if t["text"].strip() or mark[i]:
                        continue
                    left = next(
                        (k for k in range(i - 1, -1, -1) if r["tokens"][k]["text"].strip()), None
                    )
                    right = next(
                        (
                            k
                            for k in range(i + 1, len(r["tokens"]))
                            if r["tokens"][k]["text"].strip()
                        ),
                        None,
                    )
                    if left is not None and right is not None and mark[left] and mark[right]:
                        mark[i] = True
                for i, v in enumerate(mark):
                    if v:
                        r["tokens"][i]["chg"] = True


def _width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _piece(t: dict[str, Any], text: str) -> dict[str, Any]:
    p: dict[str, Any] = {"text": text, "cls": t.get("cls", "")}
    if t.get("chg"):
        p["chg"] = True
    return p


def wrap_row(tokens: list[dict[str, Any]], cols: int) -> tuple[int, list[int]]:
    """Soft-wrap one row's tokens into visual lines without changing its text.

    Mutates tokens (splits an over-long token into pieces, copying cls and chg) and returns
    (hang, breaks): hang is the continuation indent in columns, breaks are the token indices
    where a new visual line starts.
    """
    text = "".join(t["text"] for t in tokens)
    hang = min(len(text) - len(text.lstrip(" ")) + 4, cols // 2)
    if _width(text) <= cols:
        return hang, []
    lines, cur, used, first = [], [], 0, True

    def room() -> int:
        return cols - (0 if first else hang)

    for txt in re.findall(r"\s+|\w+|[^\w\s]", text):
        if not txt.strip():
            cur.append(txt)
            used += _width(txt)
            continue
        while txt:
            if used + _width(txt) <= room():
                cur.append(txt)
                used += _width(txt)
                txt = ""
            elif any(x.strip() for x in cur):
                lines.append(cur)
                cur, used, first = [], 0, False
            else:
                n = 0
                while n < len(txt) and used + _width(txt[: n + 1]) <= room():
                    n += 1
                n = max(n, 1)
                cur.append(txt[:n])
                lines.append(cur)
                cur, used, txt, first = [], 0, txt[n:], False
    if cur:
        lines.append(cur)
    new: list[dict[str, Any]] = []
    breaks: list[int] = []
    boundaries = iter(itertools.accumulate(sum(map(len, line)) for line in lines[:-1]))
    stop = next(boundaries, None)
    offset = 0
    for token in tokens:
        txt = token["text"]
        while stop is not None and offset + len(txt) > stop:
            size = stop - offset
            if size:
                new.append(_piece(token, txt[:size]))
            breaks.append(len(new))
            txt = txt[size:]
            offset = stop
            stop = next(boundaries, None)
        if txt:
            new.append(_piece(token, txt))
        offset += len(txt)
    tokens[:] = new
    return hang, breaks


def diff_layout(scene: dict[str, Any]) -> dict[str, int]:
    rows = [dict(row) for row in scene.get("rows", [])]
    if not any("tokens" in row for row in rows):
        prepare(rows)
    nums = [row["num"] for row in rows if row.get("num") is not None]
    gutter = scene.get("gutter", math.ceil((len(str(max(nums))) + 1) * 0.72) if nums else 1)
    longest = 0
    for row in rows:
        if row.get("gap"):
            continue
        if "tokens" not in row:
            row["tokens"] = [{"text": row.get("text", ""), "cls": ""}]
            row["hang"], row["breaks"] = wrap_row(row["tokens"], 72 - gutter)
        width = 0
        for i, token in enumerate(row["tokens"]):
            if i in row.get("breaks", []):
                longest = max(longest, width)
                width = row.get("hang", 0)
            width += _width(token["text"])
        longest = max(longest, width)

    def height(font: int) -> int:
        row_height = math.floor(font * 1.75 + 0.5)
        return (
            sum(
                30 if row.get("gap") else row_height * (len(row.get("breaks", [])) + 1)
                for row in rows
            )
            + 24
            + (72 if scene.get("label") else 0)
            + 48
        )

    def top(tall: int) -> int:
        return max(118, math.floor(489 - tall / 2 + 0.5))

    font = min(40, math.floor(1560 / ((longest + gutter) * 0.6 + 2)))
    while font > 22 and top(height(font)) + height(font) > DIFF_BOTTOM:
        font -= 1
    font = max(22, font)
    tall = height(font)
    return {
        "font": font,
        "row_height": math.floor(font * 1.75 + 0.5),
        "top": top(tall),
        "height": tall,
        "bottom": top(tall) + tall,
    }

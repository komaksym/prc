"""Join-the-tokens test: every row's tokens must join to the diff line exactly.

  jointest.py tokens.json [--map map.json] [--board scene3_diff.json | --refs 453,472,...]

tokens.json:
  {"scene":3, "file":"path/in/map", "cut":4, "transform":"none"|"build",
   "refs":["453",...],                      # expected ref order (or pass --board / --refs)
   "frames":[{"t":null, "mid":false,        # mid=true: transition frame, rows may be a subset
              "rows":[{"ref":"453","tokens":["if"," ","len",...],"marker":"+"},
                      {"gap":true}]}]}
  token = "text" | {"text":..,"color":..} | ["text","color"]

Expected text of a row = transform(map_text)[cut:], transform "none" = identity,
"build" = expandtabs(4).rstrip() (what build.py fill() does). T = ''.join(token texts).
Pass iff T == expected byte for byte (codepoints, no normalization). Exit 0 on pass,
1 on failure (one line per problem, tagged [CODE]), 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ZERO_WIDTH = "​‌‍⁠﻿"
ENTITY = re.compile(r"&(?:quot|amp|lt|gt|apos|nbsp|#\d+|#x[0-9a-fA-F]+);")


def tok_text(t: Any) -> str:
    if isinstance(t, str):
        return t
    if isinstance(t, dict) and isinstance(t.get("text"), str):
        return str(t["text"])
    if isinstance(t, list) and t and isinstance(t[0], str):
        return str(t[0])
    raise ValueError(f"bad token {t!r}")


def line_index(m: dict[str, Any], path: Any) -> dict[str, dict[str, Any]]:
    f = next((f for f in m["files"] if f["path"] == path), None)
    if f is None:
        raise ValueError(f"file {path!r} not in map")
    by: dict[str, dict[str, Any]] = {}
    for h in f["hunks"]:
        for ln in h["lines"]:
            by[f"-{ln['old']}" if ln["op"] == "-" else str(ln["new"])] = ln
    return by


def describe(got: str, exp: str, ref_text: str) -> list[str]:
    """Return list of failure codes explaining why got != exp."""
    codes = []
    if (
        got[:2] in ("+ ", "- ", "− ")
        or (got[:1] in "+-−" and got[1:] == exp)
        or (got[:1] in "+-−" and got[2:] == exp)
    ):
        codes.append("MARKER")
    if " " in got:
        codes.append("NBSP")
    if any(c in got for c in ZERO_WIDTH):
        codes.append("ZEROWIDTH")
    if "\r" in got:
        codes.append("CR")
    if "\n" in got:
        codes.append("NEWLINE")
    if "\t" in got or "\t" in ref_text:
        codes.append("TAB")
    if ENTITY.search(got) and not ENTITY.search(exp):
        codes.append("ENTITY")
    if got != got.rstrip() and exp == exp.rstrip():
        codes.append("TRAILING_WS")
    if (
        got == got.lstrip()
        and exp != exp.lstrip()
        and got.strip() == exp.strip()
        or len(got) - len(got.lstrip(" ")) != len(exp) - len(exp.lstrip(" "))
        and got.strip() == exp.strip()
    ):
        codes.append("INDENT")
    if (
        got != exp
        and unicodedata.normalize("NFC", got) == got
        and unicodedata.normalize("NFC", exp) == got
        and exp != got
    ):
        codes.append("NFC")
    if (
        got != exp
        and unicodedata.normalize("NFC", exp) != exp
        and got == unicodedata.normalize("NFC", exp)
        and "NFC" not in codes
    ):
        codes.append("NFC")
    if "[!code" in exp and "[!code" not in got:
        codes.append("TRANSFORMER")
    if got and exp.startswith(got) and len(got) < len(exp) and "TRANSFORMER" not in codes:
        codes.append("TRUNCATED")
    if got == "" and exp != "":
        codes.append("MISSING")
    if exp == "" and got != "" and not (set(got) <= set(ZERO_WIDTH)):
        codes.append("PLACEHOLDER")
    if re.fullmatch(r"\s*\d+\s+" + re.escape(exp), got) and exp:
        codes.append("GUTTER")
    return codes or ["MISMATCH"]


def first_diff(a: str, b: str) -> tuple[int, str]:
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i, f"U+{ord(x):04X} vs U+{ord(y):04X}"
    return min(len(a), len(b)), f"length {len(a)} vs {len(b)}"


def run(tokens: dict[str, Any], m: dict[str, Any], refs: list[str]) -> tuple[list[str], int]:
    errs = []

    def err(code: str, msg: str) -> None:
        errs.append(f"[{code}] {msg}")

    path = tokens.get("file")
    try:
        by = line_index(m, path)
    except ValueError as e:
        return [f"[INPUT] {e}"], 2
    transform = tokens.get("transform", "none")
    if transform not in ("none", "build"):
        return [f"[INPUT] unknown transform {transform!r}"], 2
    cut = tokens.get("cut")
    if not isinstance(cut, int) or isinstance(cut, bool) or cut < 0:
        return ["[INPUT] top-level 'cut' must be a non-negative integer"], 2
    if not refs:
        return ["[INPUT] no expected refs (give --board, --refs or top-level 'refs')"], 2

    def post(text: str) -> str:
        return text.expandtabs(4).rstrip() if transform == "build" else text

    texts = {}
    for r in refs:
        if r not in by:
            return [f"[INPUT] ref {r} not in map file {path}"], 2
        texts[r] = post(by[r]["text"])
    indents = [len(t) - len(t.lstrip(" ")) for t in texts.values() if t.strip()]
    common = min(indents, default=0)
    if cut not in (0, common):
        err(
            "CUT_MISMATCH",
            f"cut={cut} but allowed values are 0 (raw) or the common indent {common}",
        )
    exp: dict[str, str | None] = {}
    for r, t in texts.items():
        head = t[:cut]
        if head != " " * len(head) or len(t) < cut:
            err(
                "CUT_NOT_SPACES",
                f"row {r}: first {cut} chars {head!r} are not all ASCII spaces; cannot cut",
            )
            exp[r] = None
        else:
            exp[r] = t[cut:]

    frames = tokens.get("frames")
    if not isinstance(frames, list) or not frames:
        return ["[INPUT] no frames"], 2
    for fi, fr in enumerate(frames):
        tag = f"frame {fi} (t={fr.get('t')})"
        rows = [r for r in fr.get("rows", []) if not r.get("gap")]
        if "cut" in fr and fr["cut"] != cut:
            err("CUT_MISMATCH", f"{tag}: frame cut {fr['cut']} != {cut}")
        got_refs = [str(r.get("ref")) for r in rows]
        mid = bool(fr.get("mid") or fr.get("partial"))
        if mid:
            it = iter(refs)
            if len(set(got_refs)) != len(got_refs) or not all(g in it for g in got_refs):
                err("REF_ORDER", f"{tag}: refs {got_refs} are not an ordered subset of {refs}")
        else:
            if len(rows) != len(refs):
                err("ROW_COUNT", f"{tag}: {len(rows)} code rows, expected {len(refs)}")
            if got_refs != refs:
                err("REF_ORDER", f"{tag}: refs {got_refs}, expected {refs}")
        joined = []
        for r in rows:
            ref = str(r.get("ref"))
            want_row = exp.get(ref)
            if want_row is None:
                continue
            try:
                raw = [tok_text(t) for t in r.get("tokens", [])]
            except ValueError as e:
                err("INPUT", f"{tag} row {ref}: {e}")
                continue
            for t in raw:
                if "\n" in t:
                    err("MULTILINE_TOKEN", f"{tag} row {ref}: token {t!r} spans lines")
            T = "".join(raw)
            marker = r.get("marker")
            if marker is not None and marker not in ("+", "-", "−", "", " "):
                err("MARKER", f"{tag} row {ref}: marker field {marker!r} is not a marker")
            joined.append(T)
            if mid and T == "":
                continue
            if want_row != T:
                codes = describe(T, want_row, by[ref]["text"])
                if mid:
                    codes = ["MIDFRAME"] + codes
                i, why = first_diff(T, want_row)
                err(
                    codes[0] if len(codes) == 1 else "+".join(codes),
                    f"{tag} row {ref}: T != expected at index {i} ({why})\n    got      {T!r}\n    expected {want_row!r}",
                )
        if not mid and not errs:
            block = "\n".join(joined)
            want = "\n".join(str(exp[r]) for r in refs)
            if block != want:
                err("BLOCK", f"{tag}: rows joined with newline differ from expected block")
    return errs, (1 if errs else 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tokens")
    ap.add_argument("--map", required=True)
    ap.add_argument("--board")
    ap.add_argument("--refs")
    a = ap.parse_args(argv)
    try:
        tokens = json.loads(Path(a.tokens).read_text())
        m = json.loads(Path(a.map).read_text())
        if a.refs:
            refs = a.refs.split(",")
        elif a.board:
            b = json.loads(Path(a.board).read_text())
            sc = b["scenes"][0] if "scenes" in b else b
            refs = [str(r["ref"]) for r in (sc.get("rows") or sc["lines"]) if "ref" in r]
        else:
            refs = [str(x) for x in tokens.get("refs", [])]
    except (OSError, ValueError, KeyError) as e:
        print(f"[INPUT] {e}")
        return 2
    errs, rc = run(tokens, m, refs)
    for msg in errs:
        print(msg)
    n = sum(
        len([r for r in f.get("rows", []) if not r.get("gap")]) for f in tokens.get("frames", [])
    )
    print(
        f"{'FAIL' if rc else 'PASS'}: {Path(a.tokens).name} ({n} code rows, {len(errs)} problems)"
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())

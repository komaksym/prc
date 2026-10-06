"""Stage 5: the PR card (card.png) and the PR comment (comment.md with Mermaid).

Failure modes from docs/mvp/PLAN.md, each one a test here. Written before the
implementation; they fail until `prc.presentation.card` and
`prc.presentation.comment` exist.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from prc.identity import to_jsonable
from prc.presentation import card, comment
from tests.map_sample import shop_map

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "tests" / "data" / "explainer" / "maps"
DOCS_ONLY = json.loads((ROOT / "tests" / "data" / "card" / "docs_only.json").read_text())


def load_map(name: str) -> dict:
    return json.loads((MAPS / f"{name}.json").read_text())


def shop_dict() -> dict:
    return to_jsonable(shop_map())


def large_dict(changed: int = 20) -> dict:
    """A synthetic map with `changed` changed symbols in one call chain."""
    symbols = [
        {
            "id": f"src/pkg/mod.py::func_{i:03d}",
            "path": "src/pkg/mod.py",
            "qualname": f"func_{i:03d}",
            "kind": "function",
            "status": "modified",
            "span": [i, i + 2],
            "base_span": [i, i + 2],
            "added": 3,
            "removed": 1,
            "hunks": [],
            "call_sites": i % 5,
        }
        for i in range(changed)
    ]
    edges = [
        {
            "source": f"src/pkg/mod.py::func_{i:03d}",
            "target": f"src/pkg/mod.py::func_{i + 1:03d}",
            "status": "added" if i % 2 else "kept",
            "resolution": "exact",
        }
        for i in range(changed - 1)
    ]
    tour = [{"focus": [], "kind": "overview", "via": None}]
    tour += [{"focus": [s["id"]], "kind": "entry", "via": None} for s in symbols]
    tour.append({"focus": [], "kind": "summary", "via": None})
    return {
        "pr": "acme/big#99",
        "url": None,
        "title": "Grow the chain",
        "author": "bot",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "brief": {
            "pr": "acme/big#99",
            "title": "Grow the chain",
            "head_sha": "b" * 40,
            "files": [
                {
                    "path": "src/pkg/mod.py",
                    "kind": "code",
                    "added": 60,
                    "removed": 20,
                    "named": True,
                    "sensitive": None,
                }
            ],
            "checks": [{"name": "ci", "state": "passed"}],
            "mismatches": [],
            "look_first": [],
        },
        "files": [],
        "symbols": symbols,
        "edges": edges,
        "tour": tour,
    }


def changed_ids(m: dict) -> set[str]:
    return {s["id"] for s in m["symbols"] if s["status"] in ("added", "modified", "deleted")}


def edge_status(m: dict) -> dict[tuple[str, str], str]:
    return {(e["source"], e["target"]): e["status"] for e in m["edges"]}


# --- Mermaid edges exist in map.json with the same status ---


@pytest.mark.parametrize("name", ["pr12", "pr17", "pr14"])
def test_mermaid_edges_exist_in_map_with_same_status(name: str) -> None:
    m = load_map(name)
    block = comment.mermaid_block(m)
    known = edge_status(m)
    edges = re.findall(r"(n\d+)\s+(-->|-\.->|---)\s+(n\d+)", block)
    assert edges, "diagram must contain at least one edge"
    ids = comment.select_nodes(m)
    index = {f"n{i + 1}": sid for i, sid in enumerate(ids)}
    want = {"-->": "added", "-.->": "removed", "---": "kept"}
    for src, form, dst in edges:
        assert (index[src], index[dst]) in known, f"{src}->{dst} is not in map.json"
        assert known[index[src], index[dst]] == want[form], f"wrong status for {src}->{dst}"


def test_mermaid_edges_match_shop_map() -> None:
    m = shop_dict()
    block = comment.mermaid_block(m)
    assert comment.check_mermaid(block) == []
    known = edge_status(m)
    ids = comment.select_nodes(m)
    index = {f"n{i + 1}": sid for i, sid in enumerate(ids)}
    for src, form, dst in re.findall(r"(n\d+)\s+(-->|-\.->|---)\s+(n\d+)", block):
        assert (index[src], index[dst]) in known


# --- Mermaid labels survive hostile input ---


def test_mermaid_label_fuzz() -> None:
    hostile = '" `backtick` <angle> [sq] (par) {brace} |pipe| #hash ;semi;\nnewline\x00\x07'
    label = comment.mermaid_label(hostile)
    assert "`" not in label and '"' not in label and "<" not in label and ">" not in label
    assert "\n" not in label and "\x00" not in label
    assert re.search(r"#(?!35;|quot;|lt;|gt;)", label) is None, label
    long_label = comment.mermaid_label("n" * 200)
    assert len(long_label) <= 60
    m = shop_dict()
    m["symbols"][2]["qualname"] = hostile
    block = comment.mermaid_block(m)
    assert comment.check_mermaid(block) == []


def test_grammar_gate_rejects_bad_diagram() -> None:
    assert comment.check_mermaid("flowchart LR\nn1 --> n2") == []
    assert comment.check_mermaid('flowchart LR\nn1["a`b"]') != []
    assert comment.check_mermaid('flowchart LR\nn1["say "hi""]') != []
    assert comment.check_mermaid("flowchart LR\nn1 --> n9") != []
    assert comment.check_mermaid("graph TD\nn1 --> n2") != []


# --- 12-node cap ---


def test_mermaid_node_cap_and_truncation_line() -> None:
    m = large_dict(20)
    ids = comment.select_nodes(m)
    assert len(ids) <= 12
    block = comment.mermaid_block(m)
    assert len(re.findall(r'n\d+\["', block)) <= 12
    assert comment.check_mermaid(block) == []
    text = comment.render_comment(m)
    assert "Showing 12 of 20 changed symbols. Full map: map.html" in text


def test_small_map_has_no_truncation_line() -> None:
    text = comment.render_comment(shop_dict())
    assert "Showing" not in text
    assert "Full map" not in text


# --- Card numbers equal a recomputation from map.json/brief ---


def recompute(m: dict) -> dict[str, object]:
    brief = m["brief"]
    changed = [s for s in m["symbols"] if s["status"] in ("added", "modified", "deleted")]
    test_paths = {f["path"] for f in brief["files"] if f["kind"] == "test"}
    test_symbols = {s["id"] for s in m["symbols"] if s["path"] in test_paths}
    callers = {e["target"] for e in m["edges"] if e["source"] in test_symbols}
    checks = brief.get("checks", [])
    passed = sum(1 for c in checks if c["state"] == "passed")
    return {
        "files": len(brief["files"]),
        "symbols": len(changed),
        "sites": sum(s["call_sites"] for s in changed),
        "tests": sum(1 for f in brief["files"] if f["kind"] == "test"),
        "ci": "no CI" if not checks else f"{passed}/{len(checks)}",
        "untested": sorted(
            s["id"] for s in changed if s["path"] not in test_paths and s["id"] not in callers
        ),
    }


@pytest.mark.parametrize("name", ["pr12", "pr17", "pr14"])
def test_card_numbers_equal_map_json_recomputation(name: str) -> None:
    m = load_map(name)
    stats = card.compute_stats(m)
    want = recompute(m)
    assert stats.files == want["files"]
    assert stats.symbols_changed == want["symbols"]
    assert stats.call_sites == want["sites"]
    assert stats.tests_touched == want["tests"]
    assert stats.ci_text == want["ci"]
    assert [u.id for u in card.untested(m)] == want["untested"]
    html = card.build_card_html(m, m["brief"], None)
    for value in (stats.files, stats.symbols_changed, stats.call_sites, stats.tests_touched):
        assert str(value) in html
    assert stats.ci_text in html


def test_card_numbers_equal_shop_recomputation() -> None:
    m = shop_dict()
    stats = card.compute_stats(m)
    want = recompute(m)
    assert (stats.files, stats.symbols_changed, stats.call_sites) == (
        want["files"],
        want["symbols"],
        want["sites"],
    )
    assert [u.id for u in card.untested(m)] == want["untested"]


# --- Card order, headline, risky ---


def test_card_part_order_and_headline() -> None:
    m = shop_dict()
    board = {"scenes": [{"type": "title", "say": ["Board headline wins."]}]}
    html = card.build_card_html(m, m["brief"], board)
    assert "Board headline wins." in html
    nos = [card.build_card_html(m, m["brief"], None).find(m["title"])]
    assert nos[0] >= 0
    order = ["headline", "stats", "look-first", "risky", "untested", "computed from the code"]
    positions = [html.lower().find(part) for part in order]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions), positions


def test_card_look_first_shows_three_tour_symbols_with_files() -> None:
    m = shop_dict()
    entries = card.look_first(m)
    assert len(entries) == 3
    html = card.build_card_html(m, m["brief"], None)
    for entry in entries:
        assert entry.name in html
        assert entry.path in html


# --- Comment order, span(), Mermaid never via span() ---


def test_comment_part_order_and_span() -> None:
    m = shop_dict()
    text = comment.render_comment(m)
    assert text.startswith("# ")
    order = [
        "![PR card](card.png)",
        "```mermaid",
        "Look here first",
        "Risky",
        "Not covered by tests",
        m["head_sha"][:12],
    ]
    positions = [text.find(part) for part in order]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions), positions
    fence = text.split("```mermaid")[1].split("```")[0]
    assert "`" not in fence, "Mermaid labels never go through span()"
    body = text.split("```")[2]
    assert re.search(r"`[^`\n]+`", body) is not None, "PR strings use span()"


def test_comment_risky_and_mismatches_come_from_brief() -> None:
    m = shop_dict()
    text = comment.render_comment(m)
    assert ".github/workflows/ci.yml" in text
    assert "CI workflow" in text


# --- Docs-only PR ---


def test_docs_only_pr_gives_valid_card_and_comment() -> None:
    html = card.build_card_html(DOCS_ONLY, DOCS_ONLY["brief"], None)
    assert "No code symbols changed" in html
    stats = card.compute_stats(DOCS_ONLY)
    assert (stats.symbols_changed, stats.call_sites, stats.tests_touched) == (0, 0, 0)
    text = comment.render_comment(DOCS_ONLY)
    assert "No code symbols changed" in text
    block = comment.mermaid_block(DOCS_ONLY)
    assert comment.check_mermaid(block) == []
    assert "```mermaid" in text


# --- The picture: OCR at 800 px finds every stat and name ---


def _ocr_text(png: Path) -> str:
    small = png.with_name("card-800.png")
    subprocess.run(["sips", "-Z", "800", str(png), "--out", str(small)], check=True,
                   capture_output=True)
    out = subprocess.run(["tesseract", str(small), "stdout"], capture_output=True,
                         text=True, check=True)
    return out.stdout


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not on PATH")
@pytest.mark.skipif(shutil.which("sips") is None, reason="sips not on PATH")
def test_card_png_renders_and_ocr_finds_stats_and_names(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as driver:
            driver.chromium.launch().close()
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"Chromium cannot launch here: {str(error).splitlines()[0]}")

    m = shop_dict()
    html_path = tmp_path / "card.html"
    html_path.write_text(card.build_card_html(m, m["brief"], None))
    png = card.render_card_png(html_path, tmp_path / "card.png")
    header = png.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    import struct

    assert struct.unpack(">II", header[16:24]) == (2400, 1260)

    found = re.sub(r"[^a-z0-9]", "", _ocr_text(png).lower())
    stats = card.compute_stats(m)
    labels = ["files", "symbols", "callsites", "tests", "ci", "notest"]
    for token in [*(str(v) for v in (
        stats.files, stats.symbols_changed, stats.call_sites, stats.tests_touched,
    )), stats.ci_text.replace(" ", ""), *labels]:
        assert re.sub(r"[^a-z0-9]", "", token.lower()) in found, token
    names = [e.name for e in card.look_first(m)]
    names += [r.path for r in card.risky(m)]
    names += [u.name for u in card.untested(m)[:3]]
    for name in names:
        squashed = re.sub(r"[^a-z0-9]", "", name.lower())
        assert squashed in found, name

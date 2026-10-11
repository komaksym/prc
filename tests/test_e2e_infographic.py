from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from prc.presentation import infographic as gate

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "artifacts" / "e2e" / "infographic"
BOARD = ROOT / "tests" / "data" / "boards" / "shop.json"

LINES = [
    "Cart checkout flow",
    "2 files",
    "3 resolved call sites",
    "Look here first",
    "apply discount in cart.py",
    "Risky surfaces",
    "cart.py: external calls",
    "Direct test evidence found",
    "Infographic drawn by AI. Words from prc.",
]

ROLES: list[gate.Role] = [
    "headline",
    "chip",
    "chip",
    "label",
    "row",
    "label",
    "row",
    "verdict",
    "note",
]


def page_brief(lines: list[str]) -> gate.InfographicBrief:
    return gate.InfographicBrief(
        lines[0],
        tuple(gate.BriefLine(role, text) for role, text in zip(ROLES, lines, strict=True)),
    )


def render_lines_png(lines: list[str], path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    path.parent.mkdir(parents=True, exist_ok=True)
    items = "".join("<div>" + html.escape(line) + "</div>" for line in lines)
    ocr_style = "body{background:#fff;color:#111;font:44px/1.7 Georgia,serif;letter-spacing:2px;margin:48px}div{margin:0 0 14px}"
    html_path = path.with_suffix(".html")
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>" + ocr_style + "</style></head><body>" + items + "</body></html>"
    )
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(html_path.as_uri())
        page.screenshot(path=str(path), full_page=True)
        browser.close()
    return path


def render_html_png(
    body: str, path: Path, width: int = 1280, height: int = 720, full: bool = False
) -> Path:
    from playwright.sync_api import sync_playwright

    path.parent.mkdir(parents=True, exist_ok=True)
    style = (
        "body{margin:0;background:#fff;color:#111;font:44px Georgia,serif;letter-spacing:2px}"
        ".n{position:absolute;display:flex;align-items:center;justify-content:center}"
        ".b{border:4px solid #1d4ed8;border-radius:12px;background:#eef4ff}"
        ".f{background:#dbeafe}"
        "svg{position:absolute;left:0;top:0}"
    )
    html_path = path.with_suffix(".html")
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        + style
        + "</style></head><body>"
        + body
        + "</body></html>"
    )
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(html_path.as_uri())
        page.screenshot(path=str(path), full_page=full)
        browser.close()
    return path


ARROW = (
    "<defs><marker id='a' markerWidth='12' markerHeight='12' refX='10' refY='6' orient='auto'>"
    "<path d='M0,0 L12,6 L0,12 z' fill='#1d4ed8'/></marker></defs>"
)


def node(text: str, x: int, y: int, w: int = 380, h: int = 110, cls: str = "b") -> str:
    return (
        f"<div class='n {cls}' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px'>"
        + html.escape(text)
        + "</div>"
    )


def wire(points: list[tuple[int, int]]) -> str:
    path = " ".join(f"{x},{y}" for x, y in points)
    return (
        "<svg width='1280' height='720'>"
        + ARROW
        + f"<polyline points='{path}' fill='none' stroke='#1d4ed8' stroke-width='4' "
        "marker-end='url(#a)'/></svg>"
    )


def render_brief_png(payload: dict[str, Any], path: Path) -> Path:
    """Draw a brief as an AI artist should: text lines, then node boxes joined by arrows."""
    lines = [line["text"] for line in payload["lines"] if line["role"] != "node"]
    nodes = [line["text"] for line in payload["lines"] if line["role"] == "node"]
    links = [(rel["from"], rel["to"]) for rel in payload["relations"]]
    depth = dict.fromkeys(nodes, 0)
    for _ in nodes:
        for source, target in links:
            depth[target] = max(depth[target], depth[source] + 1)
    place: dict[str, tuple[int, int]] = {}
    rows: dict[int, int] = {}
    for text in nodes:
        col = depth[text]
        place[text] = (40 + col * 580, 40 + rows.get(col, 0) * 170)
        rows[col] = rows.get(col, 0) + 1
    width, tall = 480, 100
    boxes = "".join(node(text, x, y, w=width, h=tall) for text, (x, y) in place.items())
    wires = "".join(
        "<polyline points='"
        + f"{place[s][0] + width + 8},{place[s][1] + tall // 2} "
        + f"{place[t][0] - 6},{place[t][1] + tall // 2}"
        + "' fill='none' stroke='#1d4ed8' stroke-width='4' marker-end='url(#a)'/>"
        for s, t in links
    )
    area = 80 + max(rows.values()) * 170
    text = "".join("<div style='margin:0 48px 14px'>" + html.escape(t) + "</div>" for t in lines)
    body = (
        "<div style='padding-top:40px'>"
        + text
        + "</div>"
        + f"<div style='position:relative;height:{area}px'>"
        + boxes
        + f"<svg width='1800' height='{area}'>"
        + ARROW
        + wires
        + "</svg></div>"
    )
    return render_html_png(body, path, width=1800, height=900, full=True)


SOURCE, TARGET = "cart total", "apply discount"
SCENES: dict[str, tuple[str, bool]] = {
    "straight": (
        node(SOURCE, 100, 300) + node(TARGET, 800, 300) + wire([(484, 355), (796, 355)]),
        True,
    ),
    "vertical": (
        node(SOURCE, 450, 80) + node(TARGET, 450, 480) + wire([(640, 194), (640, 476)]),
        True,
    ),
    "elbow": (
        node(SOURCE, 100, 80)
        + node(TARGET, 800, 480)
        + wire([(484, 135), (640, 135), (640, 535), (796, 535)]),
        True,
    ),
    "bare text": (
        node(SOURCE, 100, 300, cls="")
        + node(TARGET, 800, 300, cls="")
        + wire([(440, 355), (756, 355)]),
        True,
    ),
    "one panel": (
        "<div class='n b' style='left:200px;top:120px;width:880px;height:480px'></div>"
        + node(SOURCE, 450, 200, cls="")
        + node(TARGET, 450, 400, cls=""),
        False,
    ),
    "no arrow": (node(SOURCE, 100, 300) + node(TARGET, 800, 300), False),
    "flat panels": (
        node(SOURCE, 100, 200, w=1080, cls="f") + node(TARGET, 100, 320, w=1080, cls="f"),
        False,
    ),
    "touching border": (
        node(SOURCE, 100, 200, w=1080) + node(TARGET, 100, 318, w=1080, cls="f"),
        False,
    ),
    "bordered rows": (
        "<div class='n b' style='left:40px;top:200px;width:1180px;height:70px'></div>"
        + "<div class='n b' style='left:40px;top:278px;width:1180px;height:70px'></div>"
        + node(SOURCE, 70, 205, w=260, h=60, cls="")
        + node(TARGET, 70, 283, w=420, h=60, cls=""),
        False,
    ),
}


@pytest.mark.parametrize("scene", sorted(SCENES))
def test_gate_needs_a_drawn_line_between_related_boxes(scene: str, tmp_path: Path) -> None:
    """Defect: the published infographics were stacks of text boxes that drew no structure."""
    body, drawn = SCENES[scene]
    png = render_html_png(body, tmp_path / "scene.png")
    PROOF.mkdir(parents=True, exist_ok=True)
    PROOF.joinpath(f"relation-{scene.replace(' ', '-')}.png").write_bytes(png.read_bytes())
    brief = gate.InfographicBrief(
        SOURCE,
        (gate.BriefLine("node", SOURCE), gate.BriefLine("node", TARGET)),
        (gate.Relation(SOURCE, TARGET, "call"),),
    )
    decision = gate.gate(png, brief)
    assert decision.verdict == ("pass" if drawn else "flat"), decision


def test_gate_rejects_arrowhead_that_merges_with_label(tmp_path: Path) -> None:
    body = (
        node(SOURCE, 100, 300, cls="")
        + node(TARGET, 800, 300, cls="")
        + wire([(440, 355), (840, 355)])
    )
    png = render_html_png(body, tmp_path / "overlap.png")
    PROOF.mkdir(parents=True, exist_ok=True)
    PROOF.joinpath("arrow-over-label.png").write_bytes(png.read_bytes())
    brief = gate.InfographicBrief(
        SOURCE,
        (gate.BriefLine("node", SOURCE), gate.BriefLine("node", TARGET)),
        (gate.Relation(SOURCE, TARGET, "call"),),
    )
    decision = gate.gate(png, brief)
    assert decision.verdict != "pass", decision


def run_cli(cwd: Path, *argv: str) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-m", "prc.cli", *argv],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        env=env,
    )
    assert done.returncode == 0, done.stderr
    payload: dict[str, Any] = json.loads(done.stdout)
    return payload


def test_gate_real_tesseract_images(tmp_path: Path) -> None:
    PROOF.mkdir(parents=True, exist_ok=True)
    brief = page_brief(LINES)
    good = render_lines_png(LINES, tmp_path / "good.png")
    PROOF.joinpath("flat.png").write_bytes(good.read_bytes())
    assert gate.gate(good, brief).verdict == "flat"

    bad_lines = LINES + ["watermelon quokka"]
    bad = render_lines_png(bad_lines, tmp_path / "bad.png")
    PROOF.joinpath("invented.png").write_bytes(bad.read_bytes())
    invented = gate.gate(bad, brief)
    assert invented.verdict == "invented"
    assert "watermelon" in [tok for tok, _ in invented.invented]

    wrong = [line.replace("2 files", "7 files") for line in LINES]
    wrong_png = render_lines_png(wrong, tmp_path / "wrong.png")
    PROOF.joinpath("number.png").write_bytes(wrong_png.read_bytes())
    numbered = gate.gate(wrong_png, brief)
    assert numbered.verdict == "invented"
    assert "7" in [tok for tok, _ in numbered.invented]

    dropped = [line for line in LINES if line != "apply discount in cart.py"]
    missing_png = render_lines_png(dropped, tmp_path / "missing.png")
    PROOF.joinpath("missing.png").write_bytes(missing_png.read_bytes())
    missing = gate.gate(missing_png, brief)
    assert missing.verdict == "missing"
    assert any("discount" in toks for _, toks in missing.missing)


def brief_texts(out: Path) -> list[str]:
    payload = json.loads((out / "infographic" / "brief.json").read_text())
    assert payload["disclosure"] == gate.DISCLOSURE
    return [str(line["text"]) for line in payload["lines"]]


@pytest.mark.parametrize("stage", ["version", "ocr"])
def test_explain_records_binary_tesseract_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    tool = binary / "tesseract"
    tool.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"stage = {stage!r}\n"
        "if '--version' in sys.argv and stage == 'ocr':\n"
        "    print('tesseract 5.5.0')\n"
        "else:\n"
        "    sys.stderr.buffer.write(b'\\x89bad PNG\\n')\n"
        "    sys.exit(1)\n"
    )
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("PYTHONUTF8", "1")
    candidate = render_lines_png(LINES, tmp_path / "candidate.png")
    printed = run_cli(
        tmp_path,
        "explain",
        "--source",
        "fixture:shop",
        "--store",
        str(tmp_path / "store"),
        "--out",
        str(tmp_path / "out"),
        "--infographic",
        str(candidate),
    )
    out = tmp_path / printed["out"]
    checks = json.loads((out / "infographic" / "check.json").read_text())
    assert len(checks) == 1
    assert checks[0]["verdict"] == "tool"
    assert len(checks[0]["failed_modes"]) == (4 if stage == "ocr" else 0)
    run = json.loads((out / "run.json").read_text())
    assert run["infographic"]["status"] == "failed"
    assert run["infographic"]["published_sha256"] is None
    assert not (out / "infographic.png").exists()
    assert "![PR card](card.png)" in (out / "comment.md").read_text()
    PROOF.mkdir(parents=True, exist_ok=True)
    PROOF.joinpath(f"binary-{stage}-check.json").write_text(json.dumps(checks, indent=2))
    PROOF.joinpath(f"binary-{stage}-card.png").write_bytes((out / "card.png").read_bytes())


def test_explain_publishes_first_passing_candidate(tmp_path: Path) -> None:
    first = run_cli(
        tmp_path,
        "explain",
        "--source",
        "fixture:shop",
        "--board",
        str(BOARD),
        "--voice",
        "none",
        "--store",
        str(tmp_path / "store"),
        "--out",
        str(tmp_path / "out"),
    )
    seed = tmp_path / first["out"]
    lines = brief_texts(seed)
    payload = json.loads((seed / "infographic" / "brief.json").read_text())
    assert payload["relations"], "the shop brief should give the artist calls to draw"
    bad = render_lines_png(lines + ["watermelon quokka"], tmp_path / "bad.png")
    flat = render_lines_png(lines, tmp_path / "flat.png")
    good = render_brief_png(payload, tmp_path / "good.png")
    PROOF.mkdir(parents=True, exist_ok=True)
    PROOF.joinpath("shop-flat.png").write_bytes(flat.read_bytes())
    PROOF.joinpath("shop-diagram.png").write_bytes(good.read_bytes())

    second = run_cli(
        tmp_path,
        "explain",
        "--source",
        "fixture:shop",
        "--board",
        str(BOARD),
        "--voice",
        "none",
        "--store",
        str(tmp_path / "store"),
        "--out",
        str(tmp_path / "out"),
        "--infographic",
        str(bad),
        "--infographic",
        str(flat),
        "--infographic",
        str(good),
    )
    out = tmp_path / second["out"]
    assert second["infographic"] is not None
    published = out / "infographic.png"
    assert published.read_bytes() == good.read_bytes()

    run = json.loads((out / "run.json").read_text())
    info = run["infographic"]
    assert info["status"] == "passed"
    assert info["published_sha256"] == hashlib.sha256(good.read_bytes()).hexdigest()
    assert [(a["name"], a["verdict"]) for a in info["attempts"]] == [
        ("bad.png", "invented"),
        ("flat.png", "flat"),
        ("good.png", "pass"),
    ]

    checks = json.loads((out / "infographic" / "check.json").read_text())
    assert [(c["name"], c["verdict"]) for c in checks] == [
        ("bad.png", "invented"),
        ("flat.png", "flat"),
        ("good.png", "pass"),
    ]
    assert [r["drawn"] for r in checks[1]["relations"]] == [False] * len(payload["relations"])
    assert [r["drawn"] for r in checks[2]["relations"]] == [True] * len(payload["relations"])
    assert checks[0]["sha256"] == hashlib.sha256(bad.read_bytes()).hexdigest()

    comment = (out / "comment.md").read_text()
    assert "![Infographic drawn by AI. Words from prc.](infographic.png)" in comment
    assert "![PR card](card.png)" not in comment

    doc = (out / "doc.html").read_text()
    assert "data:image/png;base64," in doc
    assert "<figcaption>Infographic drawn by AI. Words from prc.</figcaption>" in doc


def test_explain_without_infographic_keeps_card(tmp_path: Path) -> None:
    printed = run_cli(
        tmp_path,
        "explain",
        "--source",
        "fixture:shop",
        "--store",
        str(tmp_path / "store"),
        "--out",
        str(tmp_path / "out"),
    )
    out = tmp_path / printed["out"]
    run = json.loads((out / "run.json").read_text())
    assert run["infographic"]["status"] == "missing"
    assert run["infographic"]["published_sha256"] is None
    assert run["infographic"]["attempts"] == []
    assert (out / "infographic" / "brief.json").exists()
    assert json.loads((out / "infographic" / "check.json").read_text()) == []
    assert "![PR card](card.png)" in (out / "comment.md").read_text()
    assert not (out / "infographic.png").exists()


def test_explain_rejects_bad_infographic_flag(tmp_path: Path) -> None:
    stray = tmp_path / "note.txt"
    stray.write_text("not a png")
    base = [
        sys.executable,
        "-m",
        "prc.cli",
        "explain",
        "--source",
        "fixture:shop",
        "--store",
        str(tmp_path / "store"),
        "--out",
        str(tmp_path / "out"),
    ]
    missing = subprocess.run(
        [*base, "--infographic", str(tmp_path / "ghost.png")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert missing.returncode != 0
    text_flag = subprocess.run(
        [*base, "--infographic", str(stray)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert text_flag.returncode != 0

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
    "Infographic drawn by AI. Words from PRC.",
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


PANELS: dict[str, Any] = {
    "mode": "panels",
    "headline": "Missing references get an explicit result",
    "subtitle": "One status check in the handler",
    "panels": [
        {"title": "BEFORE", "lines": ["Status 404 had no name", "Callers guessed the meaning"]},
        {"title": "SWITCH", "lines": ["Handler checks the status", "Returns not found"]},
        {"title": "PROOF", "lines": ["One test covers 404"]},
    ],
    "footer": ["Start at handler.py"],
}


def render_panels_png(payload: dict[str, Any], path: Path, extra: str = "") -> Path:
    """Draw a panels brief as the prompt asks: titled panels in their key colors, arrows between
    them, and a footer bar with the key swatches."""
    lines = payload["lines"]
    text = {
        role: [ln["text"] for ln in lines if ln["role"] == role]
        for role in ("headline", "subtitle", "footer", "legend", "note")
    }
    tones = payload.get("tones") or ["context"] * sum(ln["role"] == "panel" for ln in lines)
    panels: list[tuple[str, list[str]]] = []
    for ln in lines:
        if ln["role"] == "panel":
            panels.append((ln["text"], []))
        elif ln["role"] == "item":
            panels[-1][1].append(ln["text"])
    if extra:
        panels[1][1].append(extra)
    width, gap, top = 440, 90, 230
    body = (
        "<div style='position:absolute;left:60px;top:40px;font-weight:700;font-size:46px'>"
        + html.escape(text["headline"][0])
        + "</div><div style='position:absolute;left:60px;top:120px;font-size:32px'>"
        + html.escape(text["subtitle"][0])
        + "</div>"
    )
    for k, (title, items) in enumerate(panels):
        x = 60 + k * (width + gap)
        _, _, color, tint = gate.TONES[tones[k]]
        body += (
            f"<div style='position:absolute;left:{x}px;top:{top}px;width:{width}px;height:400px;"
            f"border:6px solid {color};border-radius:12px;background:{tint}'>"
            f"<div style='background:{tint};border-bottom:6px solid {color};padding:14px 22px;"
            "font-weight:700;font-size:34px;color:#10213f'>"
            + html.escape(title)
            + "</div>"
            + "".join(
                "<div style='padding:18px 22px 0;font-size:28px;color:#10213f'>"
                + html.escape(item)
                + "</div>"
                for item in items
            )
            + "</div>"
        )
        if k:
            ax = x - gap + 10
            body += (
                "<svg width='1600' height='900'>"
                + ARROW
                + f"<line x1='{ax}' y1='{top + 200}' x2='{ax + gap - 30}' y2='{top + 200}' "
                "stroke='#1d4ed8' stroke-width='6' marker-end='url(#a)'/></svg>"
            )
    body += (
        "<div style='position:absolute;left:0;top:720px;width:1600px;height:150px;"
        "background:#dbeafe;font-size:28px'>"
        + "".join(
            f"<div style='position:absolute;left:60px;top:{24 + 56 * i}px'>"
            + html.escape(t)
            + "</div>"
            for i, t in enumerate(text["footer"] + text["note"])
        )
        + "".join(
            f"<div style='position:absolute;left:{900 + 160 * (i % 4)}px;top:{24 + 56 * (i // 4)}px;"
            "display:flex;align-items:center;gap:10px'>"
            f"<span style='width:24px;height:24px;background:{gate.TONES[tone][2]}'></span>"
            + html.escape(gate.TONES[tone][0])
            + "</div>"
            for i, tone in enumerate(dict.fromkeys(tones))
        )
        + "</div>"
    )
    return render_html_png(body, path, width=1600, height=900)


def test_gate_passes_a_panels_image_with_its_lines_and_fails_an_invented_word(
    tmp_path: Path,
) -> None:
    brief = gate.infobrief({"files": []}, None, {"infographic": PANELS, "scenes": []})
    payload = gate.brief_dict(brief)
    PROOF.mkdir(parents=True, exist_ok=True)

    good = render_panels_png(payload, tmp_path / "panels.png")
    PROOF.joinpath("panels-pass.png").write_bytes(good.read_bytes())
    decision = gate.gate(good, brief)
    assert decision.verdict == "pass", decision
    assert "relations" not in decision.detail

    bad = render_panels_png(payload, tmp_path / "panels-invented.png", extra="Faster checkout")
    PROOF.joinpath("panels-invented.png").write_bytes(bad.read_bytes())
    invented = gate.gate(bad, brief)
    assert invented.verdict == "invented", invented
    assert {"faster", "checkout"} <= {tok for tok, _ in invented.invented}


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


def brief_without_infographic(cwd: Path, board: Path = BOARD) -> Path:
    """A board build with no candidate fails by design and still writes the brief to draw."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
         "--board", str(board), "--voice", "none",
         "--store", str(cwd / "store"), "--out", str(cwd / "out")],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        env=env,
    )  # fmt: skip
    assert done.returncode == 2, done.stderr
    assert "no gated infographic published" in done.stderr
    (folder,) = [p for p in (cwd / "out").iterdir() if (p / "infographic" / "brief.json").is_file()]
    return folder


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
    assert len(checks[0]["failed_modes"]) == (5 if stage == "ocr" else 0)
    run = json.loads((out / "run.json").read_text())
    assert run["infographic"]["status"] == "failed"
    assert run["infographic"]["published_sha256"] is None
    assert not (out / "infographic.png").exists()
    assert "card.png" not in (out / "comment.md").read_text()
    assert not (out / "card.png").exists()
    PROOF.mkdir(parents=True, exist_ok=True)
    PROOF.joinpath(f"binary-{stage}-check.json").write_text(json.dumps(checks, indent=2))


def test_explain_publishes_first_passing_candidate(tmp_path: Path) -> None:
    seed = brief_without_infographic(tmp_path)
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
    assert "![Infographic drawn by AI. Words from PRC.](infographic.png)" in comment
    assert "![PR card](card.png)" not in comment

    doc = (out / "page.html").read_text()
    assert "<img src='infographic.png'" in doc
    assert "id='info-open'" in doc
    assert "data:image/png;base64," not in doc


def test_explain_without_infographic_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prc import pipeline
    from prc.explainer import render as explain_render
    from prc.fixture_source import FixtureSource
    from prc.model import PrRef
    from prc.verification import EligibilityPolicy

    data = ROOT / "tests/data/explainer/maps/pr12.json"
    board = tmp_path / "board.json"
    board.write_text(json.dumps({"scenes": [{"type": "title", "say": ["A change."], "cues": []}]}))
    monkeypatch.setattr(
        pipeline,
        "verify_board",
        lambda *a, **k: {"receipts": 1, "covered": 1, "changed": 1, "tests_added": 0},
    )
    monkeypatch.setattr(
        explain_render,
        "render",
        lambda *a, **k: explain_render.Rendered(1.0, 1, [], []),
    )
    with pytest.raises(pipeline.InfographicMissingError, match="no gated infographic published"):
        pipeline.run_explain(
            FixtureSource(repo=tmp_path, resources={}),
            PrRef("acme", "shop", 1),
            lambda: 0.0,
            EligibilityPolicy(),
            tmp_path / "out",
            board_path=board,
            map_path=data,
            voice="none",
        )
    outs = list((tmp_path / "out").glob("*"))
    assert outs, "failed build still publishes its evidence folder"
    assert (outs[0] / "infographic" / "brief.json").exists()
    assert (outs[0] / "infographic" / "check.json").exists()


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

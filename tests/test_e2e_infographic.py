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
    PROOF.joinpath("pass.png").write_bytes(good.read_bytes())
    assert gate.gate(good, brief).verdict == "pass"

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
    good = render_lines_png(lines, tmp_path / "good.png")
    bad = render_lines_png(lines + ["watermelon quokka"], tmp_path / "bad.png")

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
        ("good.png", "pass"),
    ]

    checks = json.loads((out / "infographic" / "check.json").read_text())
    assert [(c["name"], c["verdict"]) for c in checks] == [
        ("bad.png", "invented"),
        ("good.png", "pass"),
    ]
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

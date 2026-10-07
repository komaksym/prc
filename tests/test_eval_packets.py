"""Reader packets materialize the frozen viewing conditions."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval/packets.py"


@pytest.fixture
def run(tmp_path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    root = tmp_path / "run"
    out = root / "outputs/pr11"
    out.mkdir(parents=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content("<h1>Readable card</h1>")
        page.screenshot(path=str(out / "card.png"))
        browser.close()
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=1920x1080:d=2:r=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out / "video.mp4"),
        ],
        check=True,
    )
    (out / "comment.md").write_text("# Change\nExact comment text.\n")
    (out / "doc.html").write_text(
        '<h1>Visible walkthrough</h1><p style="display:none">HIDDEN ANSWER</p><div style="height:1900px">Long document</div><p>Document end</p>'
    )
    (out / "map.html").write_text(
        '<h1>Initial map</h1><div style="height:1400px"></div><p>Below viewport</p>'
    )
    (out / "board.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "type": "title",
                        "start": 0,
                        "end": 2,
                        "say": ["A change"],
                        "cues": [{"at": "A", "t": 0.2}],
                    }
                ]
            }
        )
    )
    (out / "run.json").write_text('{"duration_seconds": 2}')
    return root


def cli(run: Path, conditions: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(run), "pr11", "--conditions", conditions],
        capture_output=True,
        text=True,
    )


def png_size(path: Path) -> tuple[int, int]:
    return struct.unpack(">II", path.read_bytes()[16:24])


def test_packet_cli_materializes_the_frozen_conditions(run: Path) -> None:
    result = cli(run, "c1,c2,c3,c4,c5")
    assert result.returncode == 0, result.stderr
    folders = run / "packets/pr11"
    proof = ROOT / "artifacts/e2e/eval-packets"
    shutil.copytree(run / "packets", proof, dirs_exist_ok=True)
    for condition in ("c1", "c2", "c3", "c4", "c5"):
        folder = folders / condition
        manifest = json.loads((folder / "manifest.json").read_text())
        assert manifest["files"]
        for name in manifest["files"]:
            assert Path(name).name == name, f"reader can access source through {name}"
            assert Path(name).suffix not in {".html", ".mp4"}
            payload = folder / name
            assert payload.is_file(), f"missing materialized payload {payload}"
            assert (
                hashlib.sha256(payload.read_bytes()).hexdigest() == manifest["payload_sha256"][name]
            )
        for name, digest in manifest["source_sha256"].items():
            assert digest == hashlib.sha256((run / "outputs/pr11" / name).read_bytes()).hexdigest()
        prompt = (folder / "prompt.md").read_text()
        questions = json.loads((ROOT / "eval/questions/pr11.json").read_text())["questions"]
        assert all(question["ask"] in prompt for question in questions)
        assert '"key"' not in prompt and '"evidence"' not in prompt
    assert png_size(folders / "c1/card.png")[0] == 800
    assert (folders / "c2/comment.md").read_bytes() == (
        run / "outputs/pr11/comment.md"
    ).read_bytes()
    frames = json.loads((folders / "c3/frames.json").read_text())
    assert [frame["t"] for frame in frames] == [0.8, 1.5]
    assert all(png_size(folders / "c3" / frame["file"])[0] == 800 for frame in frames)
    assert 0 < len(frames) <= 30
    doc = (folders / "c4/doc.txt").read_text()
    assert "Visible walkthrough" in doc and "Document end" in doc and "HIDDEN ANSWER" not in doc
    assert len(list((folders / "c4").glob("doc-*.png"))) == 2
    assert png_size(folders / "c5/map.png") == (1280, 800)


def test_failed_rebuild_keeps_previous_packet_and_success_removes_stale_files(run: Path) -> None:
    assert cli(run, "c2").returncode == 0
    dest = run / "packets/pr11/c2"
    (dest / "stale.html").write_text("old source leakage")
    before = {path.name: path.read_bytes() for path in dest.iterdir()}
    comment = run / "outputs/pr11/comment.md"
    contents = comment.read_bytes()
    comment.unlink()
    assert cli(run, "c2").returncode != 0
    assert {path.name: path.read_bytes() for path in dest.iterdir()} == before
    comment.write_bytes(contents)
    assert cli(run, "c2").returncode == 0
    assert not (dest / "stale.html").exists()


@pytest.mark.parametrize("damage", ["missing-input", "untimed-board", "invalid-condition"])
def test_packet_cli_rejects_invalid_inputs(run: Path, damage: str) -> None:
    if damage == "missing-input":
        (run / "outputs/pr11/video.mp4").unlink()
    if damage == "untimed-board":
        (run / "outputs/pr11/board.json").write_text('{"scenes":[{"say":["change"]}]}')
    result = cli(run, "unknown" if damage == "invalid-condition" else "c3")
    assert result.returncode != 0

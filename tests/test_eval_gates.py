"""Release evidence must reject absent checks and incorrectly displayed facts."""

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from prc.presentation.card import build_card_html

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval/gates.py"
spec = importlib.util.spec_from_file_location("eval_gates_under_test", SCRIPT)
assert spec and spec.loader
gates: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


def test_card_gate_checks_each_label_not_number_presence(tmp_path: Path) -> None:
    m = json.loads((ROOT / "tests/data/explainer/maps/pr12.json").read_text())
    (tmp_path / "map.json").write_text(json.dumps(m))
    html = build_card_html(m)
    (tmp_path / "card.html").write_text(html)
    assert gates.gate_card_facts(tmp_path)[0]
    html = re.sub(r'(stat-value">)[^<]+', r"\g<1>999", html, count=1)
    (tmp_path / "card.html").write_text(html)
    assert not gates.gate_card_facts(tmp_path)[0]


@pytest.mark.parametrize("damage", ["missing", "sha", "line"])
def test_doc_gate_requires_the_board_receipt(tmp_path: Path, damage: str) -> None:
    m = {"pr": "owner/repo#1", "head_sha": "a" * 40, "base_sha": "b" * 40}
    board = {"scenes": [{"type": "title", "cite": [{"line": "main.py:7"}]}]}
    (tmp_path / "map.json").write_text(json.dumps(m))
    (tmp_path / "board.json").write_text(json.dumps(board))
    url = f"https://github.com/owner/repo/blob/{'a' * 40}/main.py#L7"
    (tmp_path / "doc.html").write_text(f'<a href="{url}">receipt</a>')
    assert gates.gate_doc_links(tmp_path)[0]
    damaged = (
        ""
        if damage == "missing"
        else url.replace("a" * 40, "c" * 40)
        if damage == "sha"
        else url.replace("#L7", "#L8")
    )
    (tmp_path / "doc.html").write_text(f'<a href="{damaged}">receipt</a>')
    assert not gates.gate_doc_links(tmp_path)[0]


def test_empty_run_cannot_pass_the_gate_cli(tmp_path: Path) -> None:
    (tmp_path / "outputs").mkdir()
    outcome = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True
    )
    assert outcome.returncode != 0


def test_browser_launch_failure_is_a_failed_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import playwright.sync_api

    (tmp_path / "map.json").write_text("{}")
    (tmp_path / "board.json").write_text('{"scenes":[{"type":"diff"}]}')

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("browser unavailable")

    @contextmanager
    def driver() -> Iterator[Any]:
        yield SimpleNamespace(chromium=SimpleNamespace(launch=fail))

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", driver)
    assert not gates.gate_dom_text(tmp_path)[0]


def test_narrated_video_requires_an_audio_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "video.mp4").write_bytes(b"placeholder")
    (tmp_path / "run.json").write_text('{"voice":"say"}')
    probe = {
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"}],
        "format": {"duration": "60"},
    }

    def run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, json.dumps(probe), "")

    monkeypatch.setattr(gates.subprocess, "run", run)
    assert not gates.gate_video_file(tmp_path)[0]
    (tmp_path / "run.json").write_text('{"voice":"none"}')
    assert gates.gate_video_file(tmp_path)[0]


def test_narrated_video_rejects_silent_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "video.mp4").write_bytes(b"placeholder")
    (tmp_path / "run.json").write_text('{"voice":"say"}')
    probe = {
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
            {"codec_type": "audio"},
        ],
        "format": {"duration": "60"},
    }

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if args[0] == "ffprobe":
            return subprocess.CompletedProcess(args, 0, json.dumps(probe), "")
        return subprocess.CompletedProcess(args, 0, "", "mean_volume: -inf dB\n")

    monkeypatch.setattr(gates.subprocess, "run", run)
    assert not gates.gate_video_file(tmp_path)[0]

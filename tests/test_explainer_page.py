"""Page: one storyboard drives the video and the clickable page."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tests/data/explainer/maps/pr12.json"
def _board() -> dict:
    m = json.loads(MAP.read_text())
    f = next(f for f in m["files"] if f["hunks"])
    h = f["hunks"][0]
    line = next(ln for ln in h["lines"] if ln["op"] == "+")
    ref = str(line["new"])
    return {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [ref],
                "rows": [{"ref": ref, "op": "+", "num": line["new"], "text": line["text"]}],
                "say": ["The diff adds one line."],
                "cues": [{"at": [0, 0.0], "do": "step", "n": 1}],
            },
        ]
    }
def test_page_steps_through_same_captions_with_file_and_hunk_links(tmp_path: Path) -> None:
    from prc.explainer.page import files_url, render_page
    m = json.loads(MAP.read_text())
    b = _board()
    # same captions the video would narrate
    html = render_page(b, m, tmp_path, 12.5, has_video=True, infographic=None)
    assert "A small change lands." in html
    assert "The diff adds one line." in html
    # every scene has an anchor and nav
    assert "scene-0" in html and "scene-1" in html
    assert "Scene 1 of 2" in html and "Scene 2 of 2" in html
    # file + hunk links: PR files URL with diff anchor plus blob link
    owner_repo, number = m["pr"].split("#")
    assert f"/pull/{number}/files#diff-" in html
    assert "/blob/" in html and "#L" in html
    # local diff view quotes the hunk text
    f = next(f for f in m["files"] if f["hunks"])
    assert f["path"] in html
    # not a replay: no engine, no scripts, but links to the video
    assert "engine.js" not in html and "<script" not in html
    assert 'video.mp4' in html
    # files_url is stable per path
    assert files_url(owner_repo, number, f["path"]).endswith("#diff-" + __import__("hashlib").md5(f["path"].encode()).hexdigest())
    assert (tmp_path / "page.html").is_file()
def test_page_embeds_narration_audio_per_scene_where_available(tmp_path: Path) -> None:
    from prc.explainer.page import render_page
    m = json.loads(MAP.read_text())
    b = _board()
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01_0.wav").write_bytes(b"RIFF")
    html = render_page(b, m, tmp_path, 12.5, has_video=True, infographic=None)
    assert 'audio/01_0.wav' in html
    assert "No narration audio" in html  # scene 0 has no clip

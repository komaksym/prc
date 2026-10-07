"""Frame lists for the c3 video packet (EVAL.md C).

One function: list_frames(board, duration) returns up to 30 frame specs at
800px wide — one 0.5s before each scene ends, one 0.6s after each cue fires.
No rendering here; packets.py decodes these samples into reader-facing PNGs.

Rendered boards supply exact scene bounds and cue times. Untimed boards
retain the word-count estimate, scaled to run.json duration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEAD, GAP, TAIL = 0.45, 0.3, 0.9
WORDS_PER_SECOND = 3.0
FRAME_WIDTH = 800
MAX_FRAMES = 30
SCENE_END_BACKOFF = 0.5
CUE_LEAD = 0.6


def _spoken(scene: dict[str, Any]) -> list[str]:
    out = []
    for item in scene.get("say", []):
        out.append(item["speak"] if isinstance(item, dict) else item)
    return out


def _sentence_seconds(text: str) -> float:
    return len(text.split()) / WORDS_PER_SECOND


def _scene_bounds(board: dict[str, Any], duration: float) -> list[tuple[float, float]]:
    """Use recorded bounds when available, otherwise estimate untimed scenes."""
    scenes = board.get("scenes", [])
    if all("start" in scene and "end" in scene for scene in scenes):
        return [(float(scene["start"]), float(scene["end"])) for scene in scenes]
    raw: list[float] = []
    for scene in scenes:
        sentences = _spoken(scene)
        total = LEAD + sum(_sentence_seconds(t) for t in sentences)
        total += GAP * max(0, len(sentences) - 1) + TAIL + float(scene.get("hold", 0))
        raw.append(total)
    scale = duration / sum(raw) if sum(raw) > 0 and duration > 0 else 1.0
    bounds = []
    cursor = 0.0
    for length in raw:
        end = cursor + length * scale
        bounds.append((cursor, end))
        cursor = end
    return bounds


def _cue_time(scene: dict[str, Any], start: float, end: float, phrase: str) -> float | None:
    """Character-share position of the cue phrase inside the scene window."""
    sentences = _spoken(scene)
    if not sentences or not phrase:
        return None
    for i, text in enumerate(sentences):
        offset = text.find(phrase)
        if offset < 0:
            continue
        share = (i + (offset / len(text) if text else 0)) / len(sentences)
        return start + share * (end - start)
    return None


def list_frames(
    board: dict[str, Any],
    duration: float,
    max_frames: int = MAX_FRAMES,
    width: int = FRAME_WIDTH,
) -> list[dict[str, Any]]:
    """Scene-end (end - 0.5s) and cue (cue + 0.6s) frame specs, sorted by time."""
    bounds = _scene_bounds(board, duration)
    frames: list[dict[str, Any]] = []
    for i, (scene, (start, end)) in enumerate(zip(board.get("scenes", []), bounds, strict=True)):
        t = min(max(end - SCENE_END_BACKOFF, start), duration)
        frames.append({"label": f"scene{i:02d}_end", "t": round(t, 2), "width": width})
        for cue in scene.get("cues", []):
            at = cue.get("at")
            cue_t = (
                float(cue["t"])
                if "t" in cue
                else (_cue_time(scene, start, end, at) if isinstance(at, str) else None)
            )
            if cue_t is None:
                continue
            t = min(cue_t + CUE_LEAD, duration)
            frames.append({"label": f"scene{i:02d}_cue", "t": round(t, 2), "width": width})
    frames.sort(key=lambda f: f["t"])
    return frames[:max_frames]


def frames_for_pr(out_dir: Path) -> list[dict[str, Any]]:
    """Read board.json plus run.json duration from an outputs/pr<N> folder."""
    board = json.loads((out_dir / "board.json").read_text())
    run = json.loads((out_dir / "run.json").read_text())
    return list_frames(board, float(run["duration_seconds"]))

"""Cue timing: when each sentence sounds and when each cue fires.

Phrase cues resolve with the voice when there is one (kokoro synthesizes the
prefix, say synthesizes the prefix with say) and with the character share of
the sentence when there is none, so `none` never imports Kokoro.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from prc.explainer.check import find_phrase, spoken
from prc.explainer.diffrows import DIFF_BOTTOM, diff_layout
from prc.explainer.voice import Backend, audible, estimate_seconds, pauses

LEAD, GAP, TAIL = 0.45, 0.3, 0.9
ROW_LEAD, ROW_STAGGER, ROW_ENTER = 0.25, 0.035, 0.4
REPLACE_DELAY, ROW_REVEAL, SCENE_FADE, STILL_MARGIN = 0.55, 0.45, 0.35, 0.5
OUTRO_REVEAL = 0.5


def _tail(scene: dict[str, Any]) -> float:
    return (
        2 * OUTRO_REVEAL + STILL_MARGIN
        if scene.get("type") == "outro" and scene.get("fine")
        else TAIL
    )


def estimated_scene(scene: dict[str, Any], start: float, end: float) -> dict[str, Any]:
    """Estimate cue stamps with the silent sentence schedule used by fitting."""
    s = {**scene, "start": start, "end": end, "sentences": [], "cues": []}
    cursor = start + LEAD
    for text in spoken(scene) if "say" in scene else []:
        dur = estimate_seconds(text)
        s["sentences"].append({"start": cursor, "dur": dur})
        cursor += dur + GAP

    def stamp(spec: Any) -> float | None:
        value = None
        if isinstance(spec, (int, float)) and not isinstance(spec, bool):
            value = start + spec
        elif isinstance(spec, list) and len(spec) == 2:
            k, fraction = spec
            if isinstance(k, int) and 0 <= k < len(s["sentences"]):
                sent = s["sentences"][k]
                value = sent["start"] + fraction * sent["dur"]
        elif isinstance(spec, str) and "say" in scene:
            hits = find_phrase(scene, spec)
            if len(hits) == 1:
                k, offset = hits[0]
                sent = s["sentences"][k]
                value = sent["start"] + offset / len(spoken(scene)[k]) * sent["dur"]
        return value

    for cue in scene.get("cues", []):
        fitted = {**cue, "t": stamp(cue.get("at"))}
        if "until" in cue:
            fitted["until"] = stamp(cue["until"])
        s["cues"].append(fitted)
    return s


def row_motion(scene: dict[str, Any]) -> list[dict[str, list[float]]]:
    """Animation intervals consumed by the engine and coverage checks."""
    steps = {
        c["n"]: c.get("t")
        for c in scene.get("cues", [])
        if c.get("do") == "step" and isinstance(c.get("n"), int) and not isinstance(c["n"], bool)
    }
    swaps = {r.get("step", 1) for r in scene.get("rows", []) if r.get("op") == "-"}
    result = []
    for i, row in enumerate(scene.get("rows", [])):
        step = 0 if row.get("gap") else row.get("step", 0 if row.get("op") == " " else 1)
        at = steps.get(step) if step else float(scene["start"])
        reveal = float(at) if at is not None else math.inf
        if row.get("op") == "+" and step in swaps:
            reveal += REPLACE_DELAY
        result.append(
            {
                "enter": [float(scene["start"]) + ROW_LEAD + i * ROW_STAGGER, ROW_ENTER],
                "reveal": [reveal, ROW_REVEAL],
            }
        )
    return result


def visible_rows(scene: dict[str, Any]) -> set[str]:
    """Rows fully visible at the walkthrough's settled frame, before scene fade."""
    shown: set[str] = set()
    if diff_layout(scene)["bottom"] > DIFF_BOTTOM:
        return shown
    deadline = float(scene["end"]) - STILL_MARGIN
    for row, motion in zip(scene.get("rows", []), row_motion(scene), strict=True):
        ready = max(float(scene["start"]) + LEAD, sum(motion["enter"]))
        if row.get("op") == "+":
            ready = max(ready, sum(motion["reveal"]))
        if "ref" in row and ready <= deadline + 1e-6:
            shown.add(str(row["ref"]))
    return shown


def onset(scene: dict[str, Any], phrase: str, audio: Path, backend: Backend) -> tuple[float, float]:
    """When the narration starts the phrase: (prefix synthesis, character share).

    Spoken alone, the words before the phrase end where the sentence would pause
    at a comma, so a pause that starts there in the full sentence moves the onset
    to the pause's end.
    """
    ((k, offset),) = find_phrase(scene, phrase)
    s, text = scene["sentences"][k], spoken(scene)[k]
    share = (
        float(s["start"]) + float(s["on"]) + offset / len(text) * (float(s["off"]) - float(s["on"]))
    )
    before = text[:offset].rstrip()
    if not before:
        return float(s["start"]) + float(s["on"]), share
    if not backend.has_audio:
        return share, share
    wav = audio / f"{scene['i']:02d}_p{len(scene['onsets'])}.wav"
    backend.synth(before, wav)
    end = audible(wav)[1]
    gap = next(
        (
            b
            for a, b in pauses(scene["clips"][k])
            if end - 0.06 <= a <= end + 0.08 and b - a >= 0.04
        ),
        end,
    )
    return float(s["start"]) + gap, share


def at(
    scene: dict[str, Any], spec: Any, audio: Path, log: list[dict[str, Any]], backend: Backend
) -> float:
    if isinstance(spec, str):
        if spec not in scene["onsets"]:
            said, share = onset(scene, spec, audio, backend)
            scene["onsets"][spec] = said, share
            log.append(
                {
                    "scene": scene["i"],
                    "phrase": spec,
                    "said": round(said - scene["start"], 3),
                    "share": round(share - scene["start"], 3),
                }
            )
        said, share = scene["onsets"][spec]
        picked = share if not backend.has_audio else said
        return float(picked)
    if isinstance(spec, list):
        k, f = spec
        s = scene["sentences"][k]
        return float(s["start"]) + float(f) * float(s["dur"])
    return float(scene["start"]) + float(spec)


def fit_sentences(
    board: dict[str, Any], backend: Backend, audio: Path, log: list[dict[str, Any]]
) -> tuple[float, list[tuple[float, Path]]]:
    """Synthesize (or estimate) every sentence; set start/sentences/end on each scene."""
    cursor, clips = 0.0, []
    for i, s in enumerate(board["scenes"]):
        s["start"], t, s["sentences"], s["onsets"], s["clips"] = cursor, cursor + LEAD, [], {}, []
        for j, (line, speak) in enumerate(zip(s["say"], spoken(s), strict=True)):
            wav = audio / f"{i:02d}_{j}.wav"
            if backend.has_audio:
                d = backend.synth(speak, wav)
                on, off = audible(wav)
            else:
                d = estimate_seconds(speak)
                on, off = 0.0, d
            s["sentences"].append(
                {
                    "text": line if isinstance(line, str) else line["show"],
                    "start": t,
                    "dur": d,
                    "on": on,
                    "off": off,
                }
            )
            clips.append((t, wav))
            s["clips"].append(wav)
            t += d + GAP
        s["end"] = cursor = t - GAP + _tail(s) + float(s.get("hold", 0))
        for c in s.get("cues", []):
            c["t"] = at(s, c["at"], audio, log, backend)
            if "until" in c:
                c["until"] = at(s, c["until"], audio, log, backend)
        s["fade"] = [float(s["end"]) - SCENE_FADE, SCENE_FADE]
        if s["type"] == "diff":
            for row, motion in zip(s["rows"], row_motion(s), strict=True):
                row["motion"] = motion
        del s["onsets"], s["clips"]
    board["duration"] = cursor
    return cursor, clips


def estimate(board: dict[str, Any]) -> float:
    """Seconds of video without synthesizing: words at 3 per second plus pauses."""
    words = sum(len(t.split()) for s in board["scenes"] for t in spoken(s))
    hold = sum(
        LEAD + _tail(s) + s.get("hold", 0) + GAP * (len(s["say"]) - 1) for s in board["scenes"]
    )
    return float(words) / 3.0 + float(hold)


def predict(board: dict[str, Any], backend: Backend) -> float:
    """Duration the render will produce, before synthesizing.

    With `none` this is exact: sentence estimates plus the same lead, gap,
    tail and hold constants the render uses. With a voice it is the check
    formula, the best available before synthesis.
    """
    if backend.has_audio:
        return estimate(board)
    wins = scene_windows(board)
    return wins[-1][1] if wins else 0.0


def scene_windows(board: dict[str, Any]) -> list[tuple[float, float]]:
    """(start, end) per scene under voice-none timing.

    Exact for voice none (the same sentence estimates and lead, gap, tail
    and hold constants the render fits with); an approximation for voice
    backends, whose real durations are only known after synthesis.
    """
    from prc.explainer.voice import estimate_seconds as sentence_seconds

    wins: list[tuple[float, float]] = []
    cursor = 0.0
    for s in board.get("scenes", []):
        ds = [sentence_seconds(t) for t in spoken(s)] if "say" in s else []
        end = cursor + LEAD + sum(ds) + GAP * (len(ds) - 1) + _tail(s) + float(s.get("hold", 0))
        wins.append((cursor, end))
        cursor = end
    return wins


def check_stamped_cues(board: dict[str, Any], eps: float = 1e-6) -> list[str]:
    """Cues whose fitted stamp falls outside their scene, or that end before they start.

    Runs after fit_sentences sets start/end on scenes and t/until on cues,
    so it validates the actual voice-backend durations, not the estimate.
    A cue that never shows would leave its rows invisible while coverage
    counts them on screen.
    """
    problems: list[str] = []
    for i, s in enumerate(board.get("scenes", [])):
        if s.get("type") == "diff":
            if diff_layout(s)["bottom"] > DIFF_BOTTOM:
                problems.append(
                    f"scene {i}: diff cannot fit before the captions; show fewer or shorter lines"
                )
                continue
            shown = visible_rows(s)
            for row in s.get("rows", []):
                if "ref" in row and str(row["ref"]) not in shown:
                    problems.append(
                        f"scene {i}: row {row['ref']} cannot finish its reveal before the settled frame; the reveal would never show completely; "
                        "move its step cue earlier or increase hold"
                    )
        for c in s.get("cues", []):
            t = c.get("t")
            if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t):
                problems.append(f"scene {i}: cue {c.get('do')!r} needs a finite fitted timestamp")
                continue
            if float(t) < float(s["start"]) - eps or float(t) > float(s["end"]) + eps:
                problems.append(
                    f"scene {i}: cue {c.get('do')!r} stamped at {float(t):.2f}s "
                    f"is outside the scene ({float(s['start']):.2f}-"
                    f"{float(s['end']):.2f}s); the reveal would never show"
                )
            reveal = OUTRO_REVEAL * (2 if c.get("do") == "cmd" and s.get("fine") else 1)
            if (
                s.get("type") == "outro"
                and c.get("do") in ("l1", "l2", "cmd")
                and float(t) + reveal > float(s["end"]) - STILL_MARGIN + eps
            ):
                problems.append(
                    f"scene {i}: outro {c['do']!r} cannot finish its reveal before the settled frame; "
                    "move the cue earlier or increase hold"
                )
            until = c.get("until")
            if "until" in c and (
                not isinstance(until, (int, float))
                or isinstance(until, bool)
                or not math.isfinite(until)
            ):
                problems.append(f"scene {i}: cue {c.get('do')!r} needs a finite fitted end")
            elif until is not None and float(until) + eps < float(t):
                problems.append(
                    f"scene {i}: cue {c.get('do')!r} ends before it starts; "
                    "the reveal would never show"
                )
    return problems

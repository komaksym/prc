"""Cue timing: when each sentence sounds and when each cue fires.

Phrase cues resolve with the voice when there is one (kokoro synthesizes the
prefix, say synthesizes the prefix with say) and with the character share of
the sentence when there is none, so `none` never imports Kokoro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prc.explainer.check import find_phrase, spoken
from prc.explainer.voice import Backend, audible, estimate_seconds, pauses

LEAD, GAP, TAIL = 0.45, 0.3, 0.9


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
        s["end"] = cursor = t - GAP + TAIL + float(s.get("hold", 0))
        for c in s.get("cues", []):
            c["t"] = at(s, c["at"], audio, log, backend)
            if "until" in c:
                c["until"] = at(s, c["until"], audio, log, backend)
        del s["onsets"], s["clips"]
    board["duration"] = cursor
    return cursor, clips


def estimate(board: dict[str, Any]) -> float:
    """Seconds of video without synthesizing: words at 3 per second plus pauses."""
    words = sum(len(t.split()) for s in board["scenes"] for t in spoken(s))
    hold = sum(1.35 + s.get("hold", 0) + 0.3 * (len(s["say"]) - 1) for s in board["scenes"])
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
        ds = [sentence_seconds(t) for t in spoken(s)]
        end = cursor + LEAD + sum(ds) + GAP * (len(ds) - 1) + TAIL + float(s.get("hold", 0))
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
        for c in s.get("cues", []):
            t = c.get("t")
            if t is None:
                continue
            if float(t) < float(s["start"]) - eps or float(t) > float(s["end"]) + eps:
                problems.append(
                    f"scene {i}: cue {c.get('do')!r} stamped at {float(t):.2f}s "
                    f"is outside the scene ({float(s['start']):.2f}-"
                    f"{float(s['end']):.2f}s); the reveal would never show"
                )
            until = c.get("until")
            if until is not None and float(until) + eps < float(t):
                problems.append(
                    f"scene {i}: cue {c.get('do')!r} ends before it starts; "
                    "the reveal would never show"
                )
    return problems

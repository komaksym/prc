"""Materialize isolated reader packets for one comprehension run."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_spec = importlib.util.spec_from_file_location("eval_frames", _HERE / "frames.py")
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
frames_for_pr = _mod.frames_for_pr

CONDITIONS = {"c1", "c2", "c3", "c4", "c5"}
PROMPT = """Answer the frozen questions below using only the files in this folder.
Return one JSON object with an `answers` list. Each entry has its question `id`
and an `answer`. Use only the requested answer form. Do not explain answers.
For exact names, code and booleans, return only the exact value. For sets, return
a JSON array of exact items, or an empty array when none apply. For locations,
return `path::symbol`. Return `CANNOT TELL` only when this packet cannot show
the answer. For free text, use one short sentence with the requested facts.

Questions:
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _browser_capture(source: Path, dest: Path, width: int, height: int, full: bool = False) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.goto(source.resolve().as_uri(), wait_until="load")
        page.wait_for_timeout(250)
        visible_text = page.locator("body").inner_text()
        page.screenshot(path=str(dest), full_page=full)
        browser.close()
    return visible_text


def _resize(source: Path, dest: Path, width: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"scale={width}:-2:flags=lanczos",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )


def _questions(number: int) -> list[dict[str, Any]]:
    path = _ROOT / "eval/questions" / f"pr{number}.json"
    questions = json.loads(path.read_text())["questions"]
    return [{"id": q["id"], "ask": q["ask"], "type": q["type"]} for q in questions]


def _packet(out: Path, number: int, condition: str) -> None:
    questions = _questions(number)
    source_names = {
        "c1": ["card.png"],
        "c2": ["comment.md"],
        "c3": ["board.json", "run.json", "video.mp4"],
        "c4": ["doc.html"],
        "c5": ["map.html"],
    }[condition]
    sources = {name: _sha(out / name) for name in source_names}
    target = out.parent.parent / "packets" / f"pr{number}" / condition
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{condition}-", dir=target.parent))
    try:
        prompt = (
            PROMPT + "\n".join(f"{q['id']} ({q['type']}): {q['ask']}" for q in questions) + "\n"
        )
        (stage / "prompt.md").write_text(prompt)
        generated: list[str] = []
        if condition == "c1":
            _resize(out / "card.png", stage / "card.png", 800)
            generated.append("card.png")
        elif condition == "c2":
            shutil.copyfile(out / "comment.md", stage / "comment.md")
            generated.append("comment.md")
        elif condition == "c3":
            board = json.loads((out / "board.json").read_text())
            if not all("start" in s and "end" in s for s in board.get("scenes", [])):
                raise ValueError("C3 requires recorded scene and cue times")
            if any("t" not in cue for scene in board["scenes"] for cue in scene.get("cues", [])):
                raise ValueError("C3 requires recorded time for every cue")
            frames = frames_for_pr(out)
            if not frames or len(frames) > 30:
                raise ValueError("C3 requires 1 to 30 recorded frames")
            for index, frame in enumerate(frames):
                name = f"frame-{index + 1:02d}.png"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-ss",
                        str(frame["t"]),
                        "-i",
                        str(out / "video.mp4"),
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=800:-2:flags=lanczos",
                        str(stage / name),
                    ],
                    check=True,
                    capture_output=True,
                )
                frame["file"] = name
                generated.append(name)
            (stage / "frames.json").write_text(json.dumps(frames, indent=2) + "\n")
            generated.append("frames.json")
        elif condition == "c4":
            text = _browser_capture(out / "doc.html", stage / "doc-full.png", 800, 900, full=True)
            (stage / "doc.txt").write_text(text.strip() + "\n")
            generated += ["doc.txt", "doc-full.png"]
            _browser_capture(out / "doc.html", stage / "doc-first.png", 800, 900)
            generated.append("doc-first.png")
        elif condition == "c5":
            _browser_capture(out / "map.html", stage / "map.png", 1280, 800)
            generated.append("map.png")
        manifest = {
            "condition": condition,
            "files": generated + ["prompt.md"],
            "source_sha256": sources,
            "payload_sha256": {name: _sha(stage / name) for name in generated + ["prompt.md"]},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        backup = target.with_name(target.name + ".previous")
        if backup.exists() and not target.exists():
            os.replace(backup, target)
        elif backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            os.replace(target, backup)
        try:
            os.replace(stage, target)
        except OSError:
            if backup.exists():
                os.replace(backup, target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def build_packets(run_dir: Path, numbers: list[int], conditions: list[str]) -> None:
    invalid = set(conditions) - CONDITIONS
    if invalid:
        raise ValueError(f"unknown conditions: {', '.join(sorted(invalid))}")
    for number in numbers:
        out = run_dir / "outputs" / f"pr{number}"
        if not out.is_dir():
            raise FileNotFoundError(f"missing outputs for pr{number}: {out}")
        for condition in conditions:
            _packet(out, number, condition)
            print(f"pr{number} {condition}: packet materialized")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: packets.py <run_dir> <pr11,pr12> [--conditions c1,c2]", file=sys.stderr)
        return 2
    try:
        run_dir = Path(sys.argv[1]).resolve()
        numbers = [int(item.strip().lower().removeprefix("pr")) for item in sys.argv[2].split(",")]
        conditions = ["c1", "c2", "c3", "c4", "c5"]
        if "--conditions" in sys.argv[3:]:
            index = sys.argv.index("--conditions")
            conditions = sys.argv[index + 1].replace(",", " ").split()
        else:
            for item in sys.argv[3:]:
                if item.startswith("--conditions="):
                    conditions = item.partition("=")[2].replace(",", " ").split()
        build_packets(run_dir, numbers, conditions)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"packet build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

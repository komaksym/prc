"""Build reader packets for one eval run (EVAL.md C).

Run: uv run python scripts/eval/packets.py eval/runs/<label> pr11,pr12 [--conditions c1,c2,c3,c4,c5]
Reads outputs/pr<N>/{card.png,comment.md,board.json,video.mp4,doc.html,map.html,map.json,run.json}.
Writes packets/pr<N>/<cond>/{prompt.md,input files} for reader agents.
Conditions: c1 card (card.png at 800px), c2 comment (comment.md text),
c3 video (scene-end frames at 800px, max 30), c4 doc (doc.html text),
c5 map (first-screen 1280x800 screenshot).
at a time. No PNG rendering in this unit.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("eval_frames", _HERE / "frames.py")
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
frames_for_pr = _mod.frames_for_pr

PROMPT = """Answer these questions using only the files in this folder.
Quote code exactly. Answer CANNOT TELL when the files do not show the answer.
Write your answers as JSON: [{"id": "q1", "answer": "..."}, ...].
"""

# Paths are relative to packets/pr<N>/<cond>/, so ../../outputs/pr<N>/file.
REL = "../../outputs/pr{N}/{name}"


def _write(dest: Path, cond: str, files: list[str]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "prompt.md").write_text(PROMPT + f"\nCondition: {cond}.\n")
    manifest = {"condition": cond, "files": files}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def build_packets(run_dir: Path, numbers: list[int], conditions: list[str]) -> None:
    for number in numbers:
        out = run_dir / "outputs" / f"pr{number}"
        if not out.exists():
            print(f"pr{number}: no outputs, skip")
            continue
        for cond in conditions:
            dest = run_dir / "packets" / f"pr{number}" / cond
            if cond == "c1":
                # Card image at 800px; reader scales on load.
                _write(dest, cond, [REL.format(N=number, name="card.png")])
                print(f"pr{number} {cond}: packet ready (card.png, 800px)")
            elif cond == "c2":
                # Comment text copied in; image reference stays a relative link.
                (dest).mkdir(parents=True, exist_ok=True)
                (dest / "comment.md").write_text((out / "comment.md").read_text())
                _write(dest, cond, ["comment.md"])
                print(f"pr{number} {cond}: packet ready (comment.md)")
            elif cond == "c3":
                # Frame list delegated to frames.py; reader renders from video.mp4.
                frames = frames_for_pr(out)
                (dest).mkdir(parents=True, exist_ok=True)
                (dest / "frames.json").write_text(json.dumps(frames, indent=2) + "\n")
                _write(
                    dest,
                    cond,
                    ["frames.json", REL.format(N=number, name="video.mp4")],
                )
                print(f"pr{number} {cond}: packet ready ({len(frames)} frames)")
            elif cond == "c4":
                # Doc text copied in; reader reads it directly.
                (dest).mkdir(parents=True, exist_ok=True)
                (dest / "doc.html").write_text((out / "doc.html").read_text())
                _write(dest, cond, ["doc.html"])
                print(f"pr{number} {cond}: packet ready (doc.html)")
            elif cond == "c5":
                # Map first screen; reader screenshots map.html at 1280x800.
                _write(dest, cond, [REL.format(N=number, name="map.html")])
                print(f"pr{number} {cond}: packet ready (map.html first screen)")
            else:
                print(f"pr{number} {cond}: unknown condition, skip")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: packets.py <run_dir> <pr11,pr12> [--conditions c1,c2]")
        return 2
    run_dir = Path(sys.argv[1])
    numbers = [
        int(n.strip().removeprefix("pr").removeprefix("PR"))
        for n in sys.argv[2].split(",")
        if n.strip().removeprefix("pr").removeprefix("PR").lstrip("-").isdigit()
    ]
    rest = sys.argv[3:]
    conditions = ["c1", "c2", "c3", "c4", "c5"]
    for arg in rest:
        if arg.startswith("--conditions"):
            _, _, value = arg.partition("=")
            if not value and rest.index(arg) + 1 < len(rest):
                value = rest[rest.index(arg) + 1]
            conditions = [c for c in value.replace(",", " ").split() if c]
    build_packets(run_dir, numbers, conditions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

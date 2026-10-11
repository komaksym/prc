"""Rebuild the acceptance videos with a given prc binary, then run the listening gate.

Each case replays the command recorded in its render-identity.json. The previous
output moves to <acceptance>/before-<tag>/<case>/ first.
With --candidates DIR, the recorded --infographic flags are replaced by every
DIR/<case>/candidate-NN.png, in the order drawn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("acceptance", type=Path)
    parser.add_argument("--prc", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--before", required=True, help="tag for the saved previous outputs")
    parser.add_argument("--candidates", type=Path, help="folder with <case>/candidate-NN.png")
    parser.add_argument("cases", nargs="+")
    args = parser.parse_args()
    args.acceptance = args.acceptance.resolve()
    args.prc = args.prc.resolve()
    args.wheel = args.wheel.resolve()
    if args.candidates is not None:
        args.candidates = args.candidates.resolve()
    failed = []
    for case in args.cases:
        folder = args.acceptance / case
        identity = json.loads((folder / "render-identity.json").read_text())
        out = Path(identity["out"])
        saved = args.acceptance / f"before-{args.before}" / case
        saved.mkdir(parents=True, exist_ok=True)
        if out.exists():
            shutil.move(str(out), saved / "output")
        shutil.copy(folder / "render-identity.json", saved / "render-identity.json")
        command = [str(args.prc), *identity["command"][1:]]
        if args.candidates is not None:
            drawn = sorted((args.candidates / case).glob("candidate-[0-9][0-9].png"))
            if not drawn:
                failed.append(f"{case}: no candidates in {args.candidates / case}")
                continue
            command = without_infographics(command)
            for png in drawn:
                command += ["--infographic", str(png.resolve())]
            identity["infographic_candidates"] = {
                png.name: hashlib.sha256(png.read_bytes()).hexdigest() for png in drawn
            }
        started = datetime.now(UTC).isoformat()
        render = subprocess.run(command, cwd=identity["cwd"], capture_output=True, text=True)
        (folder / "cli.json").write_text(render.stdout)
        (folder / "render.log").write_text(render.stderr)
        if render.returncode != 0:
            failed.append(f"{case}: explain exited {render.returncode}")
            continue
        run = Path(json.loads(render.stdout)["out"])
        if not run.is_absolute():
            run = Path(identity["cwd"]) / run
        heard = subprocess.run([str(args.prc), "listen", str(run)], capture_output=True, text=True)
        (folder / "listen.log").write_text(heard.stdout + heard.stderr)
        if heard.returncode != 0:
            failed.append(f"{case}: listen exited {heard.returncode}")
        identity |= {
            "prc_commit": args.commit,
            "proof": str(args.wheel.parent.parent),
            "wheel": str(args.wheel),
            "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
            "command": command,
            "started_at": started,
            "completed_at": datetime.now(UTC).isoformat(),
            "out": str(run),
        }
        previous = set(identity.get("output_hashes", {}))
        names = {name for name in previous if (run / name).is_file()}
        required = {
            "map.json",
            "map.html",
            "board.json",
            "video.mp4",
            "doc.html",
            "comment.md",
            "run.json",
        }
        missing = (previous - names) & required
        if missing:
            failed.append(f"{case}: required outputs missing: {sorted(missing)}")
        names.update(
            name
            for name in (
                "map.json",
                "map.html",
                "board.json",
                "video.mp4",
                "doc.html",
                "comment.md",
                "run.json",
                "card.html",
                "card.png",
                "infographic.png",
                "infographic/brief.json",
                "infographic/check.json",
                "listening.json",
            )
            if (run / name).is_file()
        )
        identity["output_hashes"] = {
            name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in sorted(names)
        }
        identity.pop("audio_checks", None)
        (folder / "render-identity.json").write_text(json.dumps(identity, indent=1) + "\n")
        print(case, "rendered", run, "listen", heard.returncode)
    for line in failed:
        print(line, file=sys.stderr)
    return 1 if failed else 0


def without_infographics(command: list[str]) -> list[str]:
    kept: list[str] = []
    skip = False
    for part in command:
        if skip:
            skip = False
        elif part == "--infographic":
            skip = True
        else:
            kept.append(part)
    return kept


if __name__ == "__main__":
    sys.exit(main())

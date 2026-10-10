"""Rebuild the acceptance videos with a given prc binary, then run the listening gate.

Each case replays the command recorded in its render-identity.json. The previous
output moves to <acceptance>/before-<tag>/<case>/ first.
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
    parser.add_argument("cases", nargs="+")
    args = parser.parse_args()
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
        started = datetime.now(UTC).isoformat()
        render = subprocess.run(command, cwd=identity["cwd"], capture_output=True, text=True)
        (folder / "cli.json").write_text(render.stdout)
        (folder / "render.log").write_text(render.stderr)
        if render.returncode != 0:
            failed.append(f"{case}: explain exited {render.returncode}")
            continue
        run = Path(json.loads(render.stdout)["out"])
        heard = subprocess.run([str(args.prc), "listen", str(run)], capture_output=True, text=True)
        (folder / "listen.log").write_text(heard.stdout + heard.stderr)
        if heard.returncode != 0:
            failed.append(f"{case}: listen exited {heard.returncode}")
        identity |= {
            "prc_commit": args.commit,
            "wheel": str(args.wheel),
            "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
            "command": command,
            "started_at": started,
        }
        (folder / "render-identity.json").write_text(json.dumps(identity, indent=1) + "\n")
        print(case, "rendered", run, "listen", heard.returncode)
    for line in failed:
        print(line, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

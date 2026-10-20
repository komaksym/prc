"""v15 render: briefs for the infographic, then video, page and listening check per PR.

  uv run python artifacts/output-v15/render_v15.py brief    # writes infographics/SID/brief.json and prompt.md
  uv run python artifacts/output-v15/render_v15.py render   # explain with Kokoro and the gated candidate, then listen
  uv run python artifacts/output-v15/render_v15.py render v15-oauth   # rerender one PR; the roster keeps all three
"""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from prc.presentation.infographic import infobrief, write_brief_json

R = Path(__file__).resolve().parent
SIDS = ("v15-stepper", "v15-sparkline", "v15-oauth", "v15-notice", "v15-history")
sel = {p["id"]: p for p in json.loads((R / "selection.json").read_text())["prs"]}


def brief() -> None:
    for sid in sys.argv[2:] or SIDS:
        m = json.loads((R / "prepared" / sid / "map.json").read_text())
        board = json.loads((R / "boards" / sid / "board.json").read_text())
        out = write_brief_json(infobrief(m, m.get("brief"), board), R / "infographics" / sid / "brief.json")
        print(sid, out, out.with_name("prompt.md"), flush=True)


def render() -> None:
    fails, roster = [], []
    prep = R / "notes" / "prepared"
    only = sys.argv[2:] or SIDS
    for sid in SIDS:
        roster_row = {"id": sid, "pr_identity": sel[sid]["pr_identity"], "title": sel[sid]["title"]}
        if sid not in only:
            roster.append(roster_row)
            continue
        cand = R / "infographics" / sid / "candidate-01.png"
        board = R / "boards" / sid / "board.json"
        prov = json.loads((R / "prepared" / sid / "provenance.json").read_text())
        out = R / "outputs" / "final"
        out.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-m", "prc.cli", "explain", "--source", sel[sid]["url"],
               "--map", str(R / "prepared" / sid / "map.json"), "--board", str(board),
               "--git-dir", prov["git_dir"], "--voice", "kokoro", "--infographic", str(cand),
               "--out", str(out)]  # fmt: skip
        t = time.monotonic()
        d = subprocess.run(cmd, text=True, capture_output=True)
        secs = time.monotonic() - t
        if d.returncode:
            print(sid, "RENDER FAIL", d.stderr.strip().splitlines()[-3:], flush=True)
            fails.append(sid)
            continue
        o = Path(json.loads(d.stdout)["out"])
        o = o if o.is_absolute() else Path.cwd() / o
        listen = subprocess.run([sys.executable, "-m", "prc.cli", "listen", str(o)], text=True, capture_output=True)
        (prep / sid).mkdir(parents=True, exist_ok=True)
        (prep / sid / "listen.log").write_text(listen.stdout + listen.stderr)
        (prep / sid / "render-identity.json").write_text(json.dumps({
            "output": str(o), "command": cmd, "render_seconds": round(secs, 1),
            "listening_exit": listen.returncode,
            "candidate_sha256": hashlib.sha256(cand.read_bytes()).hexdigest(),
            "model": "opencode-go/muse-spark-1.3-contributor (xhigh)"}, indent=2) + "\n")  # fmt: skip
        roster.append(roster_row)
        tail = (listen.stdout + listen.stderr).strip().splitlines()[-1:]
        print(sid, "rendered", round(secs), "s, listen exit", listen.returncode, tail, flush=True)
        if listen.returncode:
            fails.append(sid + " listen")
    (R / "notes").mkdir(exist_ok=True)
    (R / "notes" / "roster.json").write_text(json.dumps(roster, indent=2) + "\n")
    (R / "notes" / "prepared_root").write_text(str(prep) + "\n")
    print("EXIT", "FAILS " + ", ".join(fails) if fails else "OK", flush=True)


{"brief": brief, "render": render}[sys.argv[1]]()

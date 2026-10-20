"""Add one PR to the v15 set: capture its pinned map, append it to selection.json, collect its evidence.

    uv run python artifacts/output-v15/add_pr.py v15-playername Tuxemon Tuxemon 3610 "front-end: Tuxemon game player name screen"
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from prc.explainer.evidence import collect

WORK = Path(__file__).resolve().parents[2]
ROOT = WORK / "artifacts/output-v15"
V4 = WORK / "artifacts/output-v4"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, check=True, text=True).stdout


def main() -> None:
    sid, owner, name, num, kind = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    spec = importlib.util.spec_from_file_location("materials", WORK / "scripts/prepare_paired_materials.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    pr = json.loads(gh("api", f"repos/{owner}/{name}/pulls/{num}"))
    out = ROOT / "prepared" / sid
    (ROOT / "source" / sid).mkdir(parents=True, exist_ok=True)
    (ROOT / "source" / sid / "pr.json").write_text(json.dumps(pr, indent=2) + "\n")
    if not (out / "map.json").exists():
        m.capture(m.GitHubSource(V4 / "git-cache", transport=m.gh_transport), m.PrRef(owner, name, num), pr["head"]["sha"], out)
    mp = json.loads((out / "map.json").read_text())
    assert mp["head_sha"] == pr["head"]["sha"]
    row = {"id": sid, "kind": kind, "pr_identity": f"{owner}/{name}#{num}", "url": pr["html_url"], "title": pr["title"],
           "head_sha": pr["head"]["sha"], "base_sha": pr["base"]["sha"], "merged_at": pr["merged_at"],
           "files": [f["path"] for f in mp["files"]]}  # fmt: skip
    sel = json.loads((ROOT / "selection.json").read_text())
    sel["prs"] = [p for p in sel["prs"] if p["id"] != sid] + [row]
    (ROOT / "selection.json").write_text(json.dumps(sel, indent=2) + "\n")
    comments = json.loads(gh("api", f"repos/{owner}/{name}/issues/{num}/comments"))
    ev = collect({"body": pr.get("body") or "", "comments": comments}, mp, out)
    print(sid, pr["html_url"], len(mp["files"]), "files", json.dumps(ev))


if __name__ == "__main__":
    main()


"""Collect real UI evidence for the three v15 PRs into prepared/<sid>/."""

import json
import subprocess
import sys
from pathlib import Path

from prc.explainer.evidence import collect

HERE = Path(__file__).resolve().parent


def main() -> None:
    sel = json.loads((HERE / "selection.json").read_text())
    for pr in sel["prs"]:
        repo, num = pr["pr_identity"].split("#")
        body = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{num}", "--jq", ".body"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        comments = json.loads(
            subprocess.run(
                ["gh", "api", f"repos/{repo}/issues/{num}/comments"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        out = HERE / "prepared" / pr["id"]
        m = json.loads((out / "map.json").read_text())
        ev = collect({"body": body, "comments": comments}, m, out)
        print(pr["id"], json.dumps(ev), file=sys.stdout)


if __name__ == "__main__":
    main()

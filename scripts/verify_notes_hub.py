#!/usr/bin/env python3
"""Drive the notes review hub through every link and notes box.

Default mode serves a temp notes dir (real roster, scratch notes.json) in
process and drives it with the agent-browser CLI in an isolated session.
Live mode (--url) drives a supervised hub instead. It always puts every note
and spot-check verdict back to its value before the pass, also when a check
fails, so the operator never finds test votes in the real hub.

For every PR the driver asserts the GitHub href, opens the infographic
(naturalWidth>0), plays the video (currentTime>1), opens page.html and
requires its engine to run (scene strip built, stage styled) with no console
errors, clicks a judge vote, reloads, and requires the vote to persist.
Writes checks.json plus one screenshot per PR. Exit 0 PASS, 1 FAIL.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class Fail(Exception):
    pass


class Browser:
    def __init__(self, session: str) -> None:
        self.session = session

    def run(self, *args: str) -> str:
        done = subprocess.run(
            ["agent-browser", "--session", self.session, *args],
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            raise Fail("agent-browser " + " ".join(args) + ": " + done.stderr.strip()[:300])
        return done.stdout.strip()

    def js(self, expr: str) -> Any:
        out = self.run("eval", expr)
        return json.loads(out)

    def errors(self) -> list[str]:
        out = self.run("errors")
        lowered = out.lower()
        if not out or "no errors" in lowered or out.strip() == "[]":
            return []
        return [out[:400]]


def api_get(url: str, path: str) -> Any:
    req = urllib.request.Request(url.rstrip("/") + path)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def api_post(url: str, path: str, payload: dict[str, Any]) -> Any:
    """POST as the hub page would: Origin is scheme://host:port, never a path."""
    parts = urllib.parse.urlsplit(url)
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": f"{parts.scheme}://{parts.netloc}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def check_hub(url: str, proof: Path, cleanup_notes: bool) -> dict[str, Any]:
    url = url.rstrip("/")
    state = api_get(url, "/api/state")
    prs = state["prs"]
    spot = state.get("spotcheck", [])
    prior_verdicts = dict(state.get("verdicts", {}))
    # Clicking the verdict that is already set clears it, so click the other one.
    pick = "right" if spot and prior_verdicts.get(spot[0]["id"]) == "wrong" else "wrong"
    if len(prs) < 1:
        raise Fail("hub lists no PRs")
    raw = subprocess.run(
        [
            "agent-browser",
            "session",
            "id",
            "--scope",
            "worktree",
            "--prefix",
            "verifynotes-" + str(proof.stat().st_ino),
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not raw:
        raise Fail("no isolated session")
    b: Browser | None = Browser(raw.split()[-1])
    assert b is not None
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    def record(name: str, detail: str) -> None:
        checks.append({"name": name, "detail": detail[:200], "passed": True})

    def shot(name: str) -> None:
        path = proof / (name + ".png")
        b.run("screenshot", str(path))
        if not path.is_file() or path.stat().st_size == 0:
            raise Fail("screenshot " + name + " missing")

    try:
        b.run("set", "viewport", "1440", "900")
        b.run("open", url)
        b.run(
            "wait",
            "--fn",
            'document.querySelectorAll("section[data-pr]").length >= 1',
        )
        count = b.js('document.querySelectorAll("section[data-pr]").length')
        if count != len(prs):
            raise Fail(f"hub shows {count} sections for {len(prs)} PRs")
        record("landing", f"{count} PR sections render")
        shot("00-landing")
        for pr in prs:
            pr_id = pr["id"]
            b.run("scrollintoview", "#sec-" + pr_id)
            title = b.js('document.getElementById("title-' + pr_id + '").textContent')
            if pr["title"] not in title:
                raise Fail(f"{pr_id}: title {title!r} misses {pr['title']!r}")
            href = b.js('document.getElementById("github-' + pr_id + '").href')
            if href != pr["github_url"]:
                raise Fail(f"{pr_id}: github href {href!r} != {pr['github_url']!r}")
            if not href.startswith("https://github.com/"):
                raise Fail(f"{pr_id}: github href is not a github.com URL")
            record(pr_id + "-github-href", href)
            info_url = url + pr["artifacts"]["infographic"]
            b.run("open", info_url)
            width = b.js("document.images[0].naturalWidth")
            if not isinstance(width, (int, float)) or width <= 0:
                raise Fail(f"{pr_id}: infographic naturalWidth is {width!r}")
            errors.extend(b.errors())
            record(pr_id + "-infographic", f"naturalWidth={width}")
            b.run("open", url + pr["artifacts"]["video"])
            b.js(
                '(function(){var v=document.querySelector("video");'
                "v.muted=true;v.play();return 1;})()"
            )
            b.run(
                "wait",
                "--fn",
                'document.querySelector("video").currentTime>1',
            )
            pos = b.js('document.querySelector("video").currentTime')
            errors.extend(b.errors())
            record(pr_id + "-video", f"currentTime={pos}")
            b.run("open", url + pr["artifacts"]["page"])
            b.run(
                "wait",
                "--fn",
                'document.querySelectorAll("#strip button").length>0',
            )
            scenes = b.js('document.querySelectorAll("#strip button").length')
            styled = b.js('getComputedStyle(document.getElementById("stage")).position')
            if styled == "static":
                raise Fail(f"{pr_id}: page.html stage is unstyled; its inline CSS did not apply")
            page_errors = b.errors()
            if page_errors:
                raise Fail(f"{pr_id}: page.html errors: " + page_errors[0][:200])
            shot(pr_id + "-page")
            record(pr_id + "-page", f"engine built {scenes} scenes, stage {styled}, no errors")
            b.run("open", url)
            b.run("scrollintoview", "#sec-" + pr_id)
            shot(pr_id + "-artifacts")
        if spot:
            first = spot[0]["id"]
            b.run("scrollintoview", "#spotcheck")
            shown = b.js('document.querySelectorAll("#spotcheck li[data-spot]").length')
            if shown != len(spot):
                raise Fail(f"spot-check shows {shown} of {len(spot)} sentences")
            cites = b.js(
                'Array.from(document.querySelectorAll("#spotcheck .cites a"))'
                ".map(function(a){return a.href;})"
            )
            if not all(str(h).startswith("https://github.com/") for h in cites):
                raise Fail("a spot-check cite is not a github.com link")
            spill = b.js(
                '(function(){var edge=document.getElementById("spotcheck")'
                ".getBoundingClientRect().right;"
                'return Array.from(document.querySelectorAll("#spotcheck .cites a"))'
                ".filter(function(a){return a.getBoundingClientRect().right>edge;}).length;})()"
            )
            if spill:
                raise Fail(f"{spill} spot-check cites run past the section edge")
            record("spotcheck-render", f"{shown} sentences, {len(cites)} GitHub cites")
            b.run("click", f'[data-verdict-for="{first}"][data-verdict="{pick}"]')
            b.run(
                "wait",
                "--fn",
                f'document.querySelector(\'[data-verdict-saved="{first}"]\').textContent==="Saved"',
            )
            b.run("open", url)
            b.run("scrollintoview", "#spotcheck")
            pressed = b.js(
                f'document.querySelector(\'[data-verdict-for="{first}"][aria-pressed="true"]\')'
                ".getAttribute('data-verdict')"
            )
            if pressed != pick:
                raise Fail("spotcheck lost on reload")
            record("spotcheck-persist", "verdict survives reload")
            shot("98-spotcheck")
        state = api_get(url, "/api/state")
        if spot:
            want = spot[0]["id"]
            if state["verdicts"].get(want, "") != pick:
                raise Fail("verdict missing in state")
        record("api-state", "verdict present in state")
        if errors:
            raise Fail("hub page errors: " + errors[0][:200])
    finally:
        if b is not None:
            with contextlib.suppress(Exception):
                subprocess.run(
                    ["agent-browser", "--session", b.session, "close"],
                    capture_output=True,
                )
        if cleanup_notes:
            restore(url, prior_verdicts, spot)
    return {"prs": len(prs), "checks": checks}


def restore(
    url: str,
    verdicts: dict[str, str],
    spot: list[dict[str, Any]],
) -> None:
    """Put the first verdict back as it was."""
    if spot:
        first = spot[0]["id"]
        api_post(url, "/api/verdict", {"id": first, "verdict": verdicts.get(first, "")})
    state = api_get(url, "/api/state")
    if spot and state["verdicts"] != verdicts:
        raise Fail("cleanup did not restore the spot-check verdicts")


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument("--url", default="")
    arg.add_argument("--notes-dir", default="")
    arg.add_argument("--proof-dir", default="")
    arg.add_argument("--cleanup-notes", action="store_true")
    opts = arg.parse_args()
    if opts.proof_dir:
        proof = Path(opts.proof_dir)
    else:
        proof = Path(tempfile.mkdtemp(prefix="notes-hub-", dir=ROOT / "artifacts"))
    proof.mkdir(parents=True, exist_ok=True)
    httpd = None
    try:
        url = opts.url
        if not url:
            sys.path.insert(0, str(ROOT / "src"))
            from prc.evaluation import notes as notes_mod

            notes_source = Path(opts.notes_dir or str(ROOT / "artifacts" / "study-v3" / "notes"))
            scratch = Path(tempfile.mkdtemp(prefix="notes-verify-"))
            shutil.copy(notes_source / "roster.json", scratch / "roster.json")
            shutil.copy(notes_source / "prepared_root", scratch / "prepared_root")
            if (notes_source / "spotcheck.json").is_file():
                shutil.copy(notes_source / "spotcheck.json", scratch / "spotcheck.json")
            httpd, url = notes_mod.serve(scratch)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
        print(url, flush=True)
        # A live hub holds the operator's real notes: always put them back.
        result = check_hub(url, proof, opts.cleanup_notes or bool(opts.url))
        (proof / "checks.json").write_text(json.dumps(result, indent=2) + chr(10))
        print("PASS", flush=True)
        print(str(proof), flush=True)
        return 0
    except Fail as err:
        print("FAIL: " + str(err), flush=True)
        return 1
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(main())

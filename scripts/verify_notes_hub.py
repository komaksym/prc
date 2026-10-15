#!/usr/bin/env python3
"""Drive the notes review hub through every link and notes box.

Default mode serves a temp notes dir (real roster, scratch notes.json) in
process and drives it with the agent-browser CLI in an isolated session.
Live mode (--url) drives a supervised hub instead, and --cleanup-notes
clears every test note afterwards so the operator starts from empty boxes.

For every PR the driver asserts the GitHub href, opens the infographic
(naturalWidth>0), plays the video (currentTime>1), opens page.html with no
console errors, types a note, reloads, and requires the note to persist.
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
    req = urllib.request.Request(url + path)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def api_post(url: str, path: str, payload: dict[str, Any], origin: str) -> Any:
    req = urllib.request.Request(
        url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def check_hub(url: str, proof: Path, cleanup_notes: bool) -> dict[str, Any]:
    state = api_get(url, "/api/state")
    prs = state["prs"]
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
                "document.title.length>0",
            )
            page_errors = b.errors()
            if page_errors:
                raise Fail(f"{pr_id}: page.html errors: " + page_errors[0][:200])
            record(pr_id + "-page", "loads with no console errors")
            b.run("open", url)
            b.run("scrollintoview", "#sec-" + pr_id)
            shot(pr_id + "-artifacts")
        for pr in prs:
            pr_id = pr["id"]
            note = "note for " + pr_id
            b.run("fill", "#notes-" + pr_id, note)
            b.run(
                "wait",
                "--fn",
                'document.getElementById("saved-' + pr_id + '").textContent==="Saved"',
            )
            record(pr_id + "-note-save", "autosave reports Saved")
        b.run("open", url)
        for pr in prs:
            pr_id = pr["id"]
            value = b.js('document.getElementById("notes-' + pr_id + '").value')
            if value != "note for " + pr_id:
                raise Fail(f"{pr_id}: note lost on reload ({value!r})")
            record(pr_id + "-note-persist", "note survives reload")
        shot("99-notes")
        state = api_get(url, "/api/state")
        for pr in prs:
            if state["notes"][pr["id"]]["text"] != "note for " + pr["id"]:
                raise Fail(pr["id"] + ": /api/state misses the typed note")
            if not state["notes"][pr["id"]]["updated_at"]:
                raise Fail(pr["id"] + ": note has no updated_at")
        record("api-state", "every typed note present with updated_at")
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
        for pr in prs:
            api_post(url, "/api/notes", {"id": pr["id"], "text": ""}, url)
        state = api_get(url, "/api/state")
        for pr in prs:
            if state["notes"][pr["id"]]["text"] != "":
                raise Fail(pr["id"] + ": cleanup left a note behind")
    return {"prs": len(prs), "checks": checks}


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
            httpd, url = notes_mod.serve(scratch)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
        print(url, flush=True)
        result = check_hub(url, proof, opts.cleanup_notes)
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

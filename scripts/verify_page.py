#!/usr/bin/env python3
"""Drive the clickable page.html like a reviewer, in an isolated headless browser.

The page directory is served over local HTTP and driven with the agent-browser
CLI. Each state gets one screenshot: every scene via the strip, one hunk panel
per code scene, narration playing, auto-advance at a scene end, the infographic
dialog and the opened Not covered toggle. The run also checks Previous and
Next, arrow keys and space, the Open on GitHub URL against sha256(path), and
the absence of CI or file-count summaries. It fails when a step breaks, the
page logs an error, or two screenshots are byte-identical. Writes report.json.
Exit 0 PASS, 1 FAIL.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import functools
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "artifacts/v3-proof/pr22"
GITHUB = re.compile(r"^https://github\.com/[^/]+/[^/]+/pull/\d+/files#diff-[0-9a-f]{64}[LR]\d+$")
VISIBLE_ROWS = (
    "Array.prototype.filter.call(document.querySelectorAll('#scale .drow:not(.gap), #scale .item'),"
    " function (e) { return parseFloat(getComputedStyle(e).opacity) > 0.5; }).length"
)


class Fail(Exception):
    pass


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


def browser_env() -> dict[str, str]:
    env = dict(os.environ)
    cache = env.get("PLAYWRIGHT_BROWSERS_PATH")
    if cache and "AGENT_BROWSER_EXECUTABLE_PATH" not in env:
        found = sorted(glob.glob(cache + "/chromium-*/chrome-mac*/*.app/Contents/MacOS/*"))
        if found:
            env["AGENT_BROWSER_EXECUTABLE_PATH"] = found[-1]
    return env


class Browser:
    def __init__(self, session: str, env: dict[str, str]) -> None:
        self.session, self.env = session, env

    def run(self, *args: str) -> str:
        done = subprocess.run(
            ["agent-browser", "--session", self.session, *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        if done.returncode != 0:
            raise Fail("agent-browser " + " ".join(args) + ": " + done.stderr.strip()[:300])
        return done.stdout.strip()

    def js(self, expr: str) -> Any:
        wrapped = "JSON.stringify((function () { return " + expr + "; })())"
        out = self.run("eval", "-b", base64.b64encode(wrapped.encode()).decode())
        value = json.loads(out)
        return json.loads(value) if isinstance(value, str) else value

    def until(self, expr: str, what: str) -> None:
        try:
            self.run("wait", "--fn", expr)
        except Fail as error:
            now = self.js("document.getElementById('counter').textContent")
            raise Fail(f"timed out waiting for {what} (page at {now!r})") from error

    def click_box(self, selector: str) -> None:
        box = self.js(
            "(function () { var r = document.querySelector("
            + json.dumps(selector)
            + ").getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()"
        )
        self.run("mouse", "move", str(round(box[0])), str(round(box[1])))
        self.run("mouse", "down")
        self.run("mouse", "up")


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument(
        "--page", default=str(PROOF / "komaksym-linkedin-automation-22-05d2b71b8690/page.html")
    )
    arg.add_argument("--shots", default=str(PROOF / "browser"))
    opts = arg.parse_args()
    page, shots = Path(opts.page), Path(opts.shots)
    if not page.is_file():
        print("FAIL: page not found: " + str(page))
        return 1
    shots.mkdir(parents=True, exist_ok=True)
    taken: dict[str, str] = {}
    checks: list[str] = []
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(page.parent))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.socket.getsockname()[1]}/{page.name}"
    raw = subprocess.run(
        ["agent-browser", "session", "id", "--scope", "worktree", "--prefix", "verifypage"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not raw:
        print("FAIL: no isolated session")
        return 1
    b = Browser(raw.split()[-1], browser_env())

    def shot(name: str) -> None:
        path = shots / (name + ".png")
        b.run("screenshot", str(path))
        if not path.is_file() or path.stat().st_size == 0:
            raise Fail("screenshot " + name + " missing")
        taken[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    def at_scene(n: int) -> None:
        b.until(
            f"document.getElementById('counter').textContent.indexOf('Scene {n} of') === 0",
            f"scene {n}",
        )

    def goto(i: int) -> None:
        b.run("click", f"#strip button:nth-child({i + 1})")
        at_scene(i + 1)

    def body_focus() -> None:
        b.js("(document.activeElement && document.activeElement.blur(), true)")

    def row_count(s: dict[str, Any]) -> int:
        if s["type"] == "diff":
            return len([r for r in s["rows"] if not r.get("gap") and "text" in r])
        return len(s["items"])

    try:
        b.run("set", "viewport", "1440", "900")
        b.run("open", url)
        b.until("window.prcPage !== undefined", "page script")
        board = b.js("window.PRC.board")
        targets = b.js("window.PRC.targets")
        scenes = board["scenes"]
        pr_url = b.js("document.querySelector('.pg-meta a').href")
        if len(scenes) < 2:
            raise Fail(f"only {len(scenes)} scene(s)")
        text = b.js("document.body.innerText")
        for banned in (r"\bno CI\b", r"\bCI (passed|failed|pending)\b", r"\b\d+ files\b", r"card"):
            if re.search(banned, text, re.I):
                raise Fail("page shows a banned summary matching " + banned)
        checks.append("no CI, file-count or card text in the page")

        for i in range(len(scenes)):
            goto(i)
            if (
                b.js(
                    "document.querySelector('#strip button.on') === "
                    f"document.querySelector('#strip button:nth-child({i + 1})')"
                )
                is not True
            ):
                raise Fail(f"strip does not mark scene {i + 1}")
            shot(f"scene-{i}")
        checks.append(f"strip reaches all {len(scenes)} scenes")

        b.run("click", "#prev")
        at_scene(len(scenes) - 1)
        b.run("click", "#next")
        at_scene(len(scenes))
        if b.js("document.getElementById('next').disabled") is not True:
            raise Fail("Next stays enabled on the last scene")
        goto(0)
        body_focus()
        b.run("press", "ArrowRight")
        at_scene(2)
        b.run("press", "ArrowLeft")
        at_scene(1)
        checks.append("Previous, Next, ArrowLeft and ArrowRight move one scene")

        code = [i for i, t in enumerate(targets) if t]
        if not code:
            raise Fail("no code scene to click")
        sample = ""
        for i in code:
            goto(i)
            regions = b.js("document.querySelectorAll('#scale .pg-hit').length")
            if regions != len(targets[i]):
                raise Fail(
                    f"scene {i + 1}: {regions} clickable regions for {len(targets[i])} targets"
                )
            k = len(targets[i]) // 2
            b.click_box(
                "#scale .pg-hit[aria-label="
                + json.dumps("Open hunk for " + targets[i][k]["label"])
                + "]"
            )
            b.until("!document.getElementById('panel').hidden", f"hunk panel on scene {i + 1}")
            s = scenes[i]
            if s["type"] == "diff":
                rows = [r for r in s["rows"] if not r.get("gap") and "text" in r]
                path, line, removed = s["file"], rows[k]["num"], rows[k]["op"] == "-"
            else:
                path, n = s["items"][k]["cite"].rsplit(":", 1)
                line, removed = abs(int(n)), int(n) < 0
            anchor = hashlib.sha256(path.encode()).hexdigest()
            want = f"{pr_url}/files#diff-{anchor}{'L' if removed else 'R'}{line}"
            href = b.js("document.getElementById('panel-gh').href")
            if href != want or not GITHUB.match(href):
                raise Fail(f"scene {i + 1} GitHub URL {href}, expected {want}")
            if b.js("document.querySelectorAll('#panel-diff tr.hk-hit').length") != 1:
                raise Fail(f"scene {i + 1} hunk does not mark the clicked line")
            if b.js("document.getElementById('panel').getBoundingClientRect().width") < 280:
                raise Fail(f"scene {i + 1} panel too narrow")
            sample = sample or href
            shot(f"scene-{i}-hunk")
            b.run("click", "#panel-close")
            b.until("document.getElementById('panel').hidden", "panel close")
        checks.append(f"hunk panel and GitHub URL on {len(code)} code scene(s)")

        first = code[0]
        goto(first)
        start = scenes[first]["start"]
        b.run("click", "#play")
        b.until(
            f"document.getElementById('narr').currentTime > {start}", "narration on the code scene"
        )
        b.run("click", "#play")
        b.until("document.getElementById('narr').paused", "pause on the code scene")
        offset = b.js("document.getElementById('narr').currentTime") - start
        if offset > 0.6:
            raise Fail(
                f"pause landed {offset:.2f} s into scene {first + 1}; too late to test the reveal"
            )
        visible, want_rows = b.js(VISIBLE_ROWS), row_count(scenes[first])
        if visible != want_rows:
            raise Fail(
                f"paused {offset:.2f} s into scene {first + 1}: {visible} of {want_rows} code rows visible"
            )
        shot("paused-code")
        checks.append(
            f"pause {offset:.2f} s into scene {first + 1} shows all {want_rows} code rows"
        )

        goto(0)
        b.run("click", "#play")
        b.until("document.getElementById('narr').currentTime > 0.3", "narration to start")
        t0 = b.js("document.getElementById('narr').currentTime")
        b.run("wait", "1200")
        t1 = b.js("document.getElementById('narr').currentTime")
        if not t1 > t0 or b.js("document.getElementById('play').textContent") != "Pause":
            raise Fail(f"Play did not advance the narration ({t0:.2f} -> {t1:.2f})")
        shot("playing")
        b.run("click", "#play")
        b.until("document.getElementById('narr').paused", "Pause")
        checks.append(f"Play advances narration {t0:.2f} -> {t1:.2f} s; Pause stops it")

        body_focus()
        b.run("press", "Space")
        b.until("!document.getElementById('narr').paused", "space to play")
        b.run("press", "Space")
        b.until("document.getElementById('narr').paused", "space to pause")
        checks.append("space toggles narration")

        end = scenes[0]["end"]
        b.js(f"(document.getElementById('narr').currentTime = {end - 0.6}, true)")
        b.run("click", "#play")
        at_scene(2)
        b.run("wait", "400")
        shot("auto-advanced")
        b.run("click", "#play")
        b.until("document.getElementById('narr').paused", "pause after auto-advance")
        checks.append("narration crossing a scene end advances to scene 2")

        b.run("click", "#info-open")
        b.until(
            "document.getElementById('info').open && document.querySelector('#info img').naturalWidth > 100",
            "infographic dialog",
        )
        shot("infographic")
        b.run("press", "Escape")
        b.until("!document.getElementById('info').open", "infographic close")
        checks.append("infographic opens in one click and closes with Escape")

        if b.js("document.querySelector('#not-covered').tagName") == "DETAILS":
            b.run("scrollintoview", "#not-covered")
            closed = b.js("document.getElementById('not-covered').open")
            b.run("click", "#not-covered summary")
            b.until("document.getElementById('not-covered').open", "Not covered toggle")
            summary = b.js("document.querySelector('#not-covered summary').textContent")
            items = b.js("document.querySelectorAll('#not-covered li').length")
            line_links = b.js("document.querySelectorAll('#not-covered a[href*=\"#L\"]').length")
            if closed or not re.fullmatch(r"Not covered: \d+ of \d+ changed lines", summary):
                raise Fail(f"Not covered summary wrong: {summary!r} (initially open {closed})")
            if items > 8 or line_links:
                raise Fail(f"Not covered lists {items} items and {line_links} line links")
            shot("notcovered-open")
            checks.append(f"{summary}; opened list has {items} entries")

        errors = b.run("errors")
        if errors and "no errors" not in errors.lower() and errors != "[]":
            raise Fail("page errors: " + errors[:300])

        seen: dict[str, str] = {}
        for name, digest in taken.items():
            if digest in seen:
                raise Fail(name + ".png is byte-identical to " + seen[digest] + ".png")
            seen[digest] = name
        (shots / "report.json").write_text(
            json.dumps(
                {
                    "page": str(page),
                    "page_sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                    "checks": checks,
                    "shots": taken,
                    "github_sample": sample,
                    "verdict": "pass",
                },
                indent=2,
            )
        )
        print(f"PASS: {len(taken)} states, all screenshots differ")
        for line in checks:
            print("  " + line)
        return 0
    except Fail as error:
        (shots / "report.json").write_text(
            json.dumps(
                {
                    "page": str(page),
                    "verdict": "fail",
                    "error": str(error),
                    "checks": checks,
                    "shots": taken,
                },
                indent=2,
            )
        )
        print("FAIL: " + str(error))
        return 1
    finally:
        server.shutdown()
        with contextlib.suppress(Fail):
            b.run("close")


if __name__ == "__main__":
    sys.exit(main())

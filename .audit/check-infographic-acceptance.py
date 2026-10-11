"""Capture current local acceptance pages with artifact-bound browser evidence."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(sys.argv[1]).resolve()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for slug in ("librarysync-98", "em-5756", "swarm-116"):
        case = root / slug
        identity = json.loads((case / "render-identity.json").read_text())
        out = Path(identity["out"])
        proof = case / "screenshots"
        proof.mkdir(exist_ok=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1080})
        page = context.new_page()
        errors: list[str] = []
        requests: list[str] = []
        page.on("pageerror", lambda err, errors=errors: errors.append(str(err)))
        page.on(
            "request",
            lambda req, requests=requests: (
                requests.append(req.url) if req.url.startswith(("http:", "https:")) else None
            ),
        )
        page.goto((out / "doc.html").as_uri())
        page.locator(".infographic img").wait_for()
        assert page.locator(".infographic img").evaluate(
            "(img) => img.complete && img.naturalWidth > 0"
        )
        page.screenshot(path=str(proof / "doc.png"), full_page=True)
        page.locator(".infographic img").screenshot(path=str(proof / "infographic-inline.png"))
        page.goto((out / "map.html").as_uri())
        page.wait_for_timeout(800)
        page.screenshot(path=str(proof / "map.png"), full_page=True)
        comment = (out / "comment.md").read_text()
        matches = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", comment)
        assert any(path == "infographic.png" for _, path in matches)
        images = "".join(
            f'<figure><img style="width:100%" src="{html.escape((out / path).as_uri())}"><figcaption>{html.escape(alt)}</figcaption></figure>'
            for alt, path in matches
        )
        preview = case / "comment-preview.html"
        preview.write_text(
            '<!doctype html><meta charset="utf-8"><title>Local PR comment image preview</title><main style="max-width:1200px;margin:auto;font:18px sans-serif"><h1>Local PR comment image preview</h1>'
            + images
            + '<pre style="white-space:pre-wrap">'
            + html.escape(comment)
            + "</pre></main>"
        )
        page.goto(preview.as_uri())
        assert page.locator("img").first.evaluate("(img) => img.complete && img.naturalWidth > 0")
        page.screenshot(path=str(proof / "comment.png"), full_page=True)
        page.set_content('<video controls style="width:100%"></video>')
        page.locator("video").evaluate(
            "(video, url) => { video.src = url; video.muted = true; return video.play(); }",
            (out / "video.mp4").as_uri(),
        )
        page.wait_for_timeout(1500)
        video = page.locator("video").evaluate(
            "(v) => ({duration:v.duration,time:v.currentTime,paused:v.paused,error:v.error?.message})"
        )
        assert video["time"] > 0 and not video["paused"] and not video["error"], video
        page.screenshot(path=str(proof / "video-diff.png"))
        assert not errors and not requests, (errors, requests)
        (case / "browser-check.json").write_text(
            json.dumps(
                {
                    "page_errors": errors,
                    "remote_requests": requests,
                    "output_hashes": identity["output_hashes"],
                    "render_commit": identity["prc_commit"],
                    "video": video,
                    "comment_preview": "Local image and source preview; no GitHub posting or GitHub Markdown rendering.",
                },
                indent=2,
            )
            + "\n"
        )
        context.close()
        print(slug, "browser checked", proof, flush=True)
    browser.close()

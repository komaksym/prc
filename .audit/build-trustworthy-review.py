"""Build a local review index from current artifact records."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from urllib.parse import quote

root = Path(sys.argv[1]).resolve()
report = json.loads((root / "verification.json").read_text())
sections = []


def count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def listening_verdict(out: Path) -> str:
    path = out / "listening.json"
    if not path.is_file():
        return "Recognizer and control evidence is unavailable. Human pacing and tone review is pending."
    checked = json.loads(path.read_text())
    verdict = "passed" if checked["passed"] else "failed"
    controls = "passed" if checked["calibration"]["passed"] else "failed"
    engine = checked["engine"]
    return (
        f"Recorded recognizer and control verdict: {verdict}. Planted controls: {controls}. "
        f"Recognizer: {engine['name']} ({engine['model']}; {engine['version']}). "
        "Human pacing and tone review is pending."
    )


questions = {
    "librarysync-98": "Does the explanation make the episode ordering change clear? Check the no-watched fallback in GitHub’s Files changed view.",
    "em-5756": "Does the explanation make the touch keyboard behavior clear? Review the dependency patch and the three browser test cases.",
    "swarm-116": "Does the explanation help you review the error paths while clearly stating the limits of Go analysis?",
}
for verified in report["cases"]:
    slug = verified["case"]
    case = root / slug
    provenance = json.loads((case / "provenance.json").read_text())
    out = Path(json.loads((case / "cli.json").read_text())["out"])
    data = json.loads((out / "map.json").read_text())
    run = json.loads((out / "run.json").read_text())
    info = run["infographic"]
    facts = verified["facts"]
    stats = facts["stats"]
    cov = verified["line_coverage"]
    links = []
    for name, label in (
        ("map.html", "Interactive map"),
        ("video.mp4", "Narrated video"),
        ("doc.html", "Walkthrough"),
        ("card.png", "PR card"),
        ("comment.md", "PR comment"),
    ):
        links.append(f'<a href="{quote(str((out / name).relative_to(root)))}">{label}</a>')
    original = html.escape((case / "original.diff").read_text())
    disclosure = "Infographic drawn by AI. Words from prc."

    def rel(name: str, folder: Path = out) -> str:
        return quote(str((folder / name).relative_to(root)))

    attempt = next(
        (n for n, item in enumerate(info["attempts"], 1) if item["verdict"] == "pass"),
        None,
    )
    gate = (
        f"Recorded infographic gate pass on attempt {attempt} of {len(info['attempts'])}."
        if info["status"] == "passed"
        else f"No infographic passed the gate ({info['status']}). The card is the PR image."
    )
    visuals = (
        (
            f'<figure><img src="{rel("infographic.png")}" alt="{disclosure}">'
            f"<figcaption>{disclosure} {gate}</figcaption></figure>"
            if info["status"] == "passed"
            else f'<p class="pending">{gate}</p>'
        )
        + f'<figure><img src="{rel("card.png")}" alt="PR card computed from the code">'
        "<figcaption>PR card, computed from the code. It is the fallback when no infographic passes.</figcaption></figure>"
    )
    limits = (
        f"Symbol and call analysis is incomplete for {count(len(facts['limits']), 'file', 'files')}: "
        + ", ".join(f"{item['path']} ({item['reason']})" for item in facts["limits"])
        if facts["limits"]
        else ""
    )
    unavailable = (
        f" {count(cov['unavailable'], 'changed line has', 'changed lines have')} no diff references."
        if cov["unavailable"]
        else ""
    )
    sections.append(
        f'<section id="{slug}"><h2><a href="{html.escape(provenance["url"])}">{html.escape(data["pr"])}</a></h2>'
        f'<p>{html.escape(data["title"])}</p><p class="revision">Base {provenance["base_sha"]}<br>Head {provenance["head_sha"]}</p>'
        f"<p>{count(stats['files'], 'file', 'files')} · +{sum(f['added'] for f in data['files'])} / −{sum(f['removed'] for f in data['files'])} lines · {count(stats['tests_touched'], 'test file', 'test files')} touched</p>"
        f'<p class="coverage">{cov["shown"]} of {cov["total"]} changed lines are on screen.{unavailable}</p>'
        f"<p>{html.escape(limits) if limits else 'Python or TypeScript symbol parsing is available. Static calls do not prove runtime test coverage.'}</p>"
        "<p>The external project’s tests were not run. Receipt checks verify cited code and numeric assertions.</p>"
        f"<nav>{' '.join(links)}</nav>"
        f"{visuals}"
        f'<p>Narration voice: {html.escape(run["voice"])}. Gate records: <a href="{rel("infographic/brief.json")}">brief</a>'
        + (
            f' · <a href="{rel("infographic/check.json")}">checks</a>'
            if (out / "infographic" / "check.json").is_file()
            else ""
        )
        + "</p>"
        f'<video controls preload="metadata" poster="{slug}/screenshots/video-diff.png" src="{quote(str((out / "video.mp4").relative_to(root)))}"></video>'
        f"<details><summary>Original diff at these revisions</summary><pre>{original}</pre></details>"
        f'<p><a href="{slug}/original.diff">Original diff file</a> · <a href="{slug}/original.numstat">Original counts</a> · '
        f'<a href="{slug}/provenance.json">Input provenance</a> · <a href="{slug}/render-identity.json">Render identity and hashes</a> · '
        f'<a href="{slug}/merge-status.json">Merge evidence</a> · <a href="{slug}/browser-check.json">Browser and video proof</a></p>'
        f"<p>{html.escape(questions[slug])}</p>"
        f'<p class="pending">{html.escape(listening_verdict(out))}'
        + (
            f' <a href="{rel("listening.json")}">Listening evidence</a>'
            if (out / "listening.json").is_file()
            else ""
        )
        + "</p>"
        '<p class="pending">Your acceptance is pending.</p></section>'
    )
(root / "index.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Trustworthy PR explanation acceptance</title><style>"
    "body{margin:0;background:#ffffff;color:#1a2333;font:17px/1.6 system-ui;color-scheme:light}main{max-width:1100px;margin:auto;padding:40px 24px}"
    "h1,h2{line-height:1.25;color:#0f1c33}a{color:#0b57d0}nav{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}"
    "section{border-top:1px solid #d7dde8;margin-top:40px;padding-top:24px}.revision,pre{font:14px/1.5 ui-monospace,monospace;overflow:auto}"
    "pre{padding:20px;background:#f1f4f9;color:#1a2333;border:1px solid #d7dde8;max-height:700px}.coverage{color:#0d6e5f}.pending{color:#8a5a00}video{display:block;width:100%;margin:24px 0;background:#eef2f7}"
    "summary{cursor:pointer}details{margin:20px 0}figure{margin:24px 0}figure img{display:block;width:100%;border:1px solid #d7dde8;background:#fff}"
    "figcaption{color:#4b5b76;font-size:15px;margin-top:8px}</style></head><body><main><h1>Trustworthy PR explanation acceptance</h1>"
    "<p>Three real pull requests. Each original diff and every PRC output use the same base and head revisions.</p>"
    '<p class="pending">You are the only human reviewer. Review the combined verification report; human acceptance remains pending.</p>'
    "<p>License, package name, and publication remain separate decisions.</p>"
    "<p>Use each normal GitHub PR page as the baseline. Review its description, Files changed, discussion, checks and navigation.</p>"
    "<p>Then assess the extra help from PRC. Score each output from 1 to 5 in the acceptance worksheet.</p>"
    "<p>1 adds no help or confusion. 2 adds a small benefit. 3 adds useful context. 4 guides your review. 5 is substantial help you would use again.</p>"
    "<p>False claims and misleading omissions block acceptance regardless of scores. This repeated reading does not measure an independent speed improvement.</p>"
    "<p>The infographic gate checks detected words and connecting ink. Inspect direction, arrowheads, endpoints, dashes, and extra connectors yourself. Original diffs remain optional verification evidence.</p>"
    "<p>Each narration verdict below comes from the current output folder's listening.json. Human pacing and tone review is pending.</p>"
    '<p><a href="verification.json">Combined verification report</a> · <a href="acceptance.md">Acceptance worksheet</a></p>'
    + "".join(sections)
    + "</main></body></html>\n"
)
worksheet = [
    "# Human acceptance",
    "",
    "You are the only human reviewer.",
    "",
    "Automated verification does not decide whether these explanations help you review code.",
    "",
    "License, package name, publication, push, and PR creation remain separate decisions.",
    "",
]
for verified in report["cases"]:
    slug = verified["case"]
    worksheet.extend(
        [
            f"## {slug}",
            "",
            questions[slug],
            "",
            "Decision: pending.",
            "",
            "Factual errors: awaiting your review.",
            "",
            "Misleading omissions: awaiting your review.",
            "",
            "Rendering problems: awaiting your review.",
            "",
            "Useful for reviewing this PR: awaiting your review.",
            "",
        ]
    )
if not (root / "acceptance.md").exists():
    (root / "acceptance.md").write_text("\n".join(worksheet))
print(root / "index.html")

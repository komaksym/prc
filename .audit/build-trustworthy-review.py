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
NL = "\n"


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

PURPOSE_A_TITLE = "Artifact acceptance"
PURPOSE_B_TITLE = "Matched PR evaluation"

PURPOSE_B_BODY = (
    "The scored study is in preparation. This hub has no sealed study roster.",
    "A matched pair uses two similar, distinct PRs that you have not seen. Review each PR once, in its assigned condition.",
    "Use GitHub plus Coldtea PR Lens CI for one PR. Use GitHub plus PRC for the other PR. Both conditions include GitHub's description, Files changed, discussion, checks, and navigation.",
    "Randomize which PR receives PRC and which PR you read first. Freeze equivalent questions and the answer key before viewing either PR.",
    "Grade answers against that key. Compare equivalent question scores per pair, then summarize the pair differences. Acceptance impressions are not study scores.",
    "The three exposed acceptance packets are excluded from the unseen study pool. Reading one PR twice mixes prior learning with the explanation's contribution.",
    "Before a scored run, reconcile and freeze the pair count, question instrument, timing rules, and these two conditions. Each comparison uses distinct unseen PRs, with one scored reading per PR. Artifact acceptance is independent and is not a prerequisite for the matched study.",
)


def fresh_header_text(exposed: str) -> str:
    lines = [
        "# Human acceptance",
        "",
        "You are the only human reviewer.",
        "",
        "Agent verification runs before human acceptance. Machine proof is in verification.json and each case's browser-check.json; it does not decide whether these explanations help you review code.",
        "",
        "License, package name, publication, push, and PR creation remain separate decisions.",
        "",
        "## " + PURPOSE_A_TITLE,
        "",
        "These cases ("
        + exposed
        + ") are exposed practice and acceptance material. They are excluded from the unseen scored pool.",
        "",
        "Check each PRC output for this PR: false claims, misleading omissions, broken references, rendering problems, and audio problems. Record the decision below.",
        "",
        "GitHub code view is an optional fact-check. The retained raw diff is optional verification evidence.",
        "",
        "The agent requirement audit records direct inspection of the selected diagrams and the limits of machine checks. Human pacing and tone review remains pending.",
        "",
        "Choose accepted, changes requested, or deferred for each packet. Record concrete defects and optional preference notes. These decisions are not comprehension scores.",
        "",
        "## " + PURPOSE_B_TITLE,
        "",
        *[line for paragraph in PURPOSE_B_BODY for line in (paragraph, "")],
    ]
    return NL.join(lines)


def fresh_case_text(slug: str, url: str) -> str:
    lines = [
        "## " + slug,
        "",
        questions[slug],
        "",
        "GitHub PR: " + url + " (optional fact-check; not a first-reading baseline)",
        "",
        "Decision: pending.",
        "",
        "Factual errors: awaiting your review.",
        "",
        "Misleading omissions: awaiting your review.",
        "",
        "Broken references: awaiting your review.",
        "",
        "Rendering problems (including audio): awaiting your review.",
        "",
        "GitHub fact-check notes (optional): awaiting your review.",
        "",
    ]
    return NL.join(lines)


def migrate_case_line(line: str) -> str | None:
    retired_fields = (
        "Usefulness scores",
        "Extra help from PRC:",
        "Most useful / least useful",
        "Would use PRC",
        "Useful for reviewing this PR:",
    )
    if any(line.strip().startswith(field) for field in retired_fields):
        answer = line.partition(":")[2].strip()
        placeholders = {"", "awaiting your review.", "pending."}
        score_parts = answer.rstrip(".").split(";")
        untouched_scores = all(part.strip().endswith(" pending") for part in score_parts)
        if answer in placeholders or untouched_scores:
            return None
        return "Legacy acceptance note, excluded from study scores: " + answer
    stripped = line.strip()
    if stripped.startswith("GitHub baseline notes:"):
        return "GitHub fact-check notes (optional):" + line.split(":", 1)[1]
    if stripped.startswith("GitHub baseline:"):
        return "GitHub PR:" + line.split(":", 1)[1]
    return line


def case_section(existing: str, start: int, slugs: list[str]) -> str:
    end = len(existing)
    for other in slugs:
        nxt = existing.find("## " + other, start)
        if nxt != -1 and nxt < end:
            end = nxt
    return existing[start:end]


def migrate_worksheet(existing: str, slugs: list[str], urls: dict[str, str], exposed: str) -> str:
    parts = [fresh_header_text(exposed)]
    for slug in slugs:
        at = existing.find("## " + slug)
        if at == -1:
            parts.append(fresh_case_text(slug, urls[slug]))
            continue
        body = case_section(existing, at + len("## " + slug), slugs)
        kept: list[str] = []
        for raw in body.split(NL):
            new = migrate_case_line(raw)
            if new is None:
                continue
            kept.append(new)
        while kept and kept[0].strip() == "":
            kept.pop(0)
        section = ("## " + slug + NL + NL.join(kept)).rstrip() + NL
        while NL * 3 in section:
            section = section.replace(NL * 3, NL * 2)
        if "Broken references:" not in section:
            section = section + "Broken references: awaiting your review." + NL
        if "Decision:" not in section:
            section = section + "Decision: pending." + NL
        parts.append(section)
    return NL.join(parts)


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
slugs = [item["case"] for item in report["cases"]]
exposed = ", ".join(slugs)
(root / "index.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Trustworthy PR explanation acceptance</title><style>"
    "body{margin:0;background:#ffffff;color:#1a2333;font:17px/1.6 system-ui;color-scheme:light}main{max-width:1100px;margin:auto;padding:40px 24px}"
    "h1,h2{line-height:1.25;color:#0f1c33}a{color:#0b57d0}nav{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}"
    "section{border-top:1px solid #d7dde8;margin-top:40px;padding-top:24px}.revision,pre{font:14px/1.5 ui-monospace,monospace;overflow:auto}"
    "pre{padding:20px;background:#f1f4f9;color:#1a2333;border:1px solid #d7dde8;max-height:700px}.coverage{color:#0d6e5f}.pending{color:#8a5a00}video{display:block;width:100%;margin:24px 0;background:#eef2f7}"
    "summary{cursor:pointer}details{margin:20px 0}figure{margin:24px 0}figure img{display:block;width:100%;border:1px solid #d7dde8;background:#fff}"
    "figcaption{color:#4b5b76;font-size:15px;margin-top:8px}</style></head><body><main><h1>Trustworthy PR explanation acceptance</h1>"
    '<nav aria-label="Review tasks"><a href="#artifact-acceptance">Artifact acceptance</a><a href="#matched-evaluation">Matched PR evaluation</a><a href="#acceptance-packets">Acceptance packets</a></nav>'
    "<p>Three real pull requests. Each original diff and every PRC output use the same base and head revisions.</p>"
    '<p>You are the only human reviewer. Agent verification runs before human acceptance. Machine proof is in <a href="verification.json">the combined verification report</a> and each case\'s browser-check.json. It does not decide whether these explanations help you review code.</p>'
    "<p>License, package name, and publication remain separate decisions.</p>"
    '<section id="artifact-acceptance"><h2>' + PURPOSE_A_TITLE + "</h2>"
    "<p>These cases ("
    + exposed
    + ") are exposed practice and acceptance material. They are excluded from the unseen scored pool.</p>"
    "<p>Check each PRC output for false claims, misleading omissions, broken references, rendering problems, and audio problems.</p>"
    "<p>Choose accepted, changes requested, or deferred for each packet. Record concrete defects in the worksheet. False claims and misleading omissions require changes. Personal preferences are acceptance notes, not study scores.</p>"
    "<p>GitHub code view is an optional fact-check. The retained raw diff is optional verification evidence.</p>"
    "<p>The infographic gate checks words and connecting ink. It does not prove arrow direction, arrowheads, or correct endpoints. The selected diagrams were also inspected directly. "
    '<a href="../../../../.audit/step1-requirement-audit.md">Agent verification scope and limits</a>.</p>'
    "<p>Each narration verdict below comes from the output folder's listening.json. Human pacing and tone review remains pending.</p>"
    '<p><a href="verification.json">Combined verification report</a> · <a href="acceptance.md">Acceptance worksheet</a></p>'
    '</section><section id="matched-evaluation"><h2>'
    + PURPOSE_B_TITLE
    + "</h2>"
    + "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in PURPOSE_B_BODY)
    + '</section><h2 id="acceptance-packets">Acceptance packets</h2>'
    + "".join(sections)
    + "</main></body></html>"
    + NL
)
urls: dict[str, str] = {}
for item in report["cases"]:
    slug = item["case"]
    urls[slug] = json.loads((root / slug / "provenance.json").read_text())["url"]
sheet = root / "acceptance.md"
if sheet.exists():
    sheet.write_text(migrate_worksheet(sheet.read_text(), slugs, urls, exposed))
else:
    sheet.write_text(
        fresh_header_text(exposed)
        + NL
        + NL.join(fresh_case_text(slug, urls[slug]) for slug in slugs)
    )
print(root / "index.html")

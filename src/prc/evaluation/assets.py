"""Dark notes-review page: title, GitHub link, PRC artifacts, one notes box."""

from __future__ import annotations

import html
import re
from typing import Any


def _pr_name(pr: str) -> str:
    """owner/repo#N as the reader knows it: repo #N."""
    repo, _, number = pr.partition("#")
    return f"{repo.rsplit('/', 1)[-1]} #{number}"


def notes_page(state: dict[str, Any]) -> str:
    sections = []
    for pr in state["prs"]:
        pr_id = pr["id"]
        note = state["notes"].get(pr_id, {})
        sections.append(_pr_section(pr, str(note.get("text", ""))))
    if state.get("spotcheck"):
        spot_note = str(state["notes"].get("spotcheck", {}).get("text", ""))
        sections.append(_spotcheck_section(state["spotcheck"], state["verdicts"], spot_note))
    body = chr(10).join(sections)
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>PR notes review</title>"
        "<style>"
        ":root{color-scheme:dark;font-family:system-ui,sans-serif;"
        "color:#e6edf3;background:#0d1117}"
        "*{box-sizing:border-box}body{margin:0}main{max-width:1120px;"
        "margin:32px auto;padding:0 24px}"
        "h1{font-size:32px;margin:0 0 8px}.muted{color:#9aa7b4}"
        ".panel{background:#161b22;border:1px solid #30363d;border-radius:12px;"
        "padding:24px;margin:24px 0}"
        ".actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}"
        "a.link{font:inherit;border:1px solid #3d444d;border-radius:8px;"
        "padding:11px 17px;background:#21262d;color:#c9e3ff;text-decoration:none}"
        "textarea{font:inherit;width:100%;min-height:120px;resize:vertical;"
        "padding:10px;border:1px solid #3d444d;border-radius:6px;"
        "background:#0d1117;color:#e6edf3}"
        "label{display:block;margin:12px 0}"
        "img.shot{width:100%;border:1px solid #30363d;border-radius:8px}"
        "video.clip{width:100%;border:1px solid #30363d;border-radius:8px;"
        "background:#000}"
        "#error{color:#ff9c90;background:#2d1416;padding:14px}"
        ".saved{color:#56d364;min-height:1.4em}"
        "ol.spot{padding-left:24px}ol.spot li{margin:0 0 22px}"
        ".where{margin:0 0 4px;color:#8b949e;font-size:13px}"
        ".cap{margin:12px 0 4px;color:#8b949e;font-size:13px}"
        ".sent{font-size:18px;margin:0 0 6px}.judge{margin:0 0 6px;color:#c9d1d9}"
        ".cites{display:flex;flex-wrap:wrap;gap:4px 12px}"
        ".cites a{color:#c9e3ff;overflow-wrap:anywhere}"
        ".verdict{display:flex;gap:10px;align-items:center;margin-top:8px}"
        ".verdict button{font:inherit;border:1px solid #3d444d;border-radius:8px;"
        "padding:7px 14px;background:#21262d;color:#e6edf3;cursor:pointer}"
        ".verdict button[aria-pressed=true]{background:#1f6feb;border-color:#1f6feb}"
        "[hidden]{display:none!important}"
        "@media(max-width:600px){main{padding:0 14px}.panel{padding:17px}}"
        "</style></head><body><main>"
        "<h1>PR notes review</h1>"
        '<p class="muted">One notes box per PR. Notes save automatically '
        "and survive a hub restart.</p>"
        '<p id="error" role="alert" hidden></p>' + body + "<script>"
        "var timers={};"
        "function showError(msg){"
        'var box=document.getElementById("error");'
        "box.textContent=msg;box.hidden=false;}"
        "function saved(id){"
        'var el=document.querySelector("[data-saved-for=\'"+id+"\']");'
        'if(el){el.textContent="Saved";}}'
        "function queue(id){"
        'var mark=document.querySelector("[data-saved-for=\'"+id+"\']");'
        'if(mark){mark.textContent="Saving...";}'
        "clearTimeout(timers[id]);"
        "timers[id]=setTimeout(function(){save(id);},500);}"
        "function save(id){"
        'var box=document.querySelector("[data-notes-id=\'"+id+"\']");'
        "if(!box){return;}"
        'fetch("/api/notes",{method:"POST",'
        'headers:{"Content-Type":"application/json"},'
        "body:JSON.stringify({id:id,text:box.value})}).then(function(r){"
        'if(!r.ok){throw new Error("save failed");}return r.json();'
        "}).then(function(){saved(id);}).catch(function(e){showError(e.message);});}"
        'document.querySelectorAll("textarea[data-notes-id]").forEach('
        'function(box){box.addEventListener("input",function(){'
        'queue(box.getAttribute("data-notes-id"));});});'
        'document.querySelectorAll("button[data-verdict-for]").forEach(function(btn){'
        'btn.addEventListener("click",function(){'
        'var id=btn.getAttribute("data-verdict-for");'
        'var pick=btn.getAttribute("aria-pressed")==="true"?"":btn.getAttribute("data-verdict");'
        'var mark=document.querySelector("[data-verdict-saved=\'"+id+"\']");'
        'mark.textContent="Saving...";'
        'fetch("/api/verdict",{method:"POST",headers:{"Content-Type":"application/json"},'
        "body:JSON.stringify({id:id,verdict:pick})}).then(function(r){"
        'if(!r.ok){throw new Error("verdict save failed");}'
        'document.querySelectorAll("[data-verdict-for=\'"+id+"\']").forEach(function(b){'
        'b.setAttribute("aria-pressed",String(b.getAttribute("data-verdict")===pick));});'
        'mark.textContent="Saved";}).catch(function(e){showError(e.message);});});});'
        "</script></body></html>"
    )


_JUDGE_LABELS = {
    "supported": "supported",
    "partly": "partly supported",
    "unsupported": "not supported",
    "not_a_claim": "not a claim",
}


def _spotcheck_section(items: list[dict[str, Any]], verdicts: dict[str, str], note: str) -> str:
    rows = []
    for item in items:
        sid = html.escape(str(item["id"]), quote=True)
        label = _JUDGE_LABELS.get(str(item["label"]), str(item["label"]))
        cites = "".join(
            '<a href="' + html.escape(str(ev["url"]), quote=True) + '" target="_blank" '
            'rel="noopener noreferrer">' + html.escape(str(ev["text"])) + "</a>"
            for ev in item.get("evidence", [])
        )
        buttons = "".join(
            '<button type="button" data-verdict-for="' + sid + '" data-verdict="' + pick + '" '
            'aria-pressed="'
            + str(verdicts.get(str(item["id"])) == pick).lower()
            + '">'
            + text
            + "</button>"
            for pick, text in (("right", "Judge right"), ("wrong", "Judge wrong"))
        )
        rows.append(
            '<li data-spot="'
            + sid
            + '"><p class="where">'
            + html.escape(_pr_name(str(item["pr"])))
            + " · "
            + html.escape(str(item["where"]))
            + '</p><p class="sent">'
            + html.escape(str(item["text"]))
            + "</p>"
            '<p class="judge"><b>Judge: '
            + html.escape(label)
            + ".</b> "
            + html.escape(str(item["reason"]))
            + "</p>"
            + ('<p class="cites">' + cites + "</p>" if cites else "")
            + '<div class="verdict">'
            + buttons
            + '<span class="saved" data-verdict-saved="'
            + sid
            + '"></span></div></li>'
        )
    return (
        '<section class="panel" id="spotcheck"><h2>Spot-check the judge</h2>'
        '<p class="muted">A judge model labeled each sentence in the PRC outputs. '
        "These are " + str(len(items)) + " of them: the flagged ones plus random ones. "
        "The model that wrote each sentence is hidden. Read the sentence and the reason. "
        "Open a cited line when you need it. Then mark the judge right or wrong.</p>"
        '<ol class="spot">' + "".join(rows) + "</ol>"
        '<label>Notes on the judge<textarea id="notes-spotcheck" data-notes-id="spotcheck">'
        + html.escape(note)
        + "</textarea></label>"
        '<p class="saved" id="saved-spotcheck" data-saved-for="spotcheck">Saved</p>'
        "</section>"
    )


def pr_label(url: str) -> str:
    """repo #N from a GitHub pull URL: the same name the spot-check items use."""
    found = re.search(r"github\.com/[^/]+/([^/]+)/pull/(\d+)", url)
    return f"{found.group(1)} #{found.group(2)}" if found else url


def _pr_section(pr: dict[str, Any], note_text: str) -> str:
    pr_id = html.escape(str(pr["id"]), quote=True)
    title = html.escape(str(pr["title"]))
    github = html.escape(str(pr["github_url"]), quote=True)
    info = html.escape(str(pr["artifacts"]["infographic"]), quote=True)
    video = html.escape(str(pr["artifacts"]["video"]), quote=True)
    page = html.escape(str(pr["artifacts"]["page"]), quote=True)
    note = html.escape(note_text)
    return (
        '<section class="panel" id="sec-' + pr_id + '" data-pr="' + pr_id + '">'
        '<p class="where">' + html.escape(pr_label(str(pr["github_url"]))) + "</p>"
        '<h2 id="title-' + pr_id + '">' + title + "</h2>"
        '<div class="actions">'
        '<a class="link" id="github-'
        + pr_id
        + '" data-github-link="'
        + pr_id
        + '" href="'
        + github
        + '" '
        'target="_blank" rel="noopener noreferrer">Open PR on GitHub</a>'
        '<a class="link" id="page-'
        + pr_id
        + '" data-page-link="'
        + pr_id
        + '" href="'
        + page
        + '" '
        'target="_blank" rel="noopener noreferrer">Open clickable page</a>'
        "</div>"
        '<p><a id="infolink-'
        + pr_id
        + '" data-infographic-link="'
        + pr_id
        + '" href="'
        + info
        + '" '
        'target="_blank" rel="noopener noreferrer">'
        '<img class="shot" id="shot-'
        + pr_id
        + '" data-infographic-img="'
        + pr_id
        + '" src="'
        + info
        + '" '
        'alt="PRC infographic"></a></p>'
        '<p class="cap">Video walkthrough. It opens on a title card; press play.</p>'
        '<p><video class="clip" id="video-' + pr_id + '" data-video="' + pr_id + '" controls '
        'preload="metadata" src="' + video + '"></video></p>'
        '<label>Notes<textarea id="notes-'
        + pr_id
        + '" data-notes-id="'
        + pr_id
        + '">'
        + note
        + "</textarea></label>"
        '<p class="saved" id="saved-' + pr_id + '" data-saved-for="' + pr_id + '">Saved</p>'
        "</section>"
    )

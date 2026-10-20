"""Agent-drawn fallback for the baoyu infographic: brief.json -> infographic.html -> candidate PNG.

Used only when Codex image_gen fails (429 usage_limit_reached). Every word comes from brief.json.

    uv run python artifacts/output-v15/draw_infographic.py v15-stepper v15-sparkline v15-oauth
"""

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

R = Path(__file__).resolve().parent
TONES = {
    "problem": ("#D55E00", "#FBE3D3"),
    "change": ("#E69F00", "#FDF0D2"),
    "part": ("#56B4E9", "#DDF0FB"),
    "proof": ("#009E73", "#D5F1E8"),
    "context": ("#8A93A6", "#E8EAEF"),
}
NAVY = "#14213D"
# Simple icons with no letters or digit-like shapes, drawn in the panel colour.
ICONS = {
    "problem": '<circle cx="32" cy="32" r="24" fill="none" stroke="{c}" stroke-width="5"/>'
    '<path d="M21 21 L43 43 M43 21 L21 43" stroke="{c}" stroke-width="6" stroke-linecap="round"/>',
    "change": '<path d="M14 50 L18 36 L44 10 L54 20 L28 46 Z" fill="{c}" fill-opacity=".25" stroke="{c}" '
    'stroke-width="4" stroke-linejoin="round"/><path d="M38 16 L48 26" stroke="{c}" stroke-width="4"/>',
    "part": '<path d="M32 8 L56 20 L32 32 L8 20 Z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
    '<path d="M8 32 L32 44 L56 32" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
    '<path d="M8 44 L32 56 L56 44" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>',
    "proof": '<circle cx="32" cy="32" r="24" fill="none" stroke="{c}" stroke-width="5"/>'
    '<path d="M20 33 L29 42 L45 23" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>',
    "context": '<rect x="10" y="14" width="44" height="36" rx="4" fill="none" stroke="{c}" stroke-width="5"/>',
}
TONE_OF = {"BEFORE": "problem", "CHANGE": "change", "PARTS": "part", "PROOF": "proof"}


def panels(brief: dict) -> list[dict]:
    out: list[dict] = []
    for line in brief["lines"]:
        if line["role"] == "panel":
            word = line["text"].split(". ", 1)[-1]
            out.append({"head": line["text"], "tone": TONE_OF.get(word, "context"), "items": []})
        elif line["role"] == "item":
            out[-1]["items"].append(line["text"])
    return out


def card(p: dict, stacked: bool = False) -> str:
    c, tint = TONES[p["tone"]]
    icon = ICONS[p["tone"]].replace("{c}", c)
    items = "".join(f"<li>{html.escape(t)}</li>" for t in p["items"])
    body = "body stacked" if stacked else "body"
    return (
        f"<section class='card' style='background:{tint};border-color:{c}'>"
        f"<header style='background:{tint};border-bottom-color:{c}'>{html.escape(p['head'])}</header>"
        f"<div class='{body}'><svg class='icon' viewBox='0 0 64 64'>{icon}</svg>"
        f"<ul style='border-left-color:{c}'>{items}</ul></div></section>"
    )


def arrow(color: str = NAVY, vertical: bool = False) -> str:
    rot = " style='transform:rotate(90deg)'" if vertical else ""
    return (
        f"<svg class='arrow' viewBox='0 0 120 60'{rot}><path d='M6 30 H88' stroke='{color}' stroke-width='9' "
        f"stroke-linecap='round'/><path d='M80 10 L112 30 L80 50 Z' fill='{color}'/></svg>"
    )


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;font-family:'Helvetica Neue',Arial,sans-serif;color:%(navy)s;
background-color:#FBFCFE;background-image:linear-gradient(#DCE6F2 1px,transparent 1px),linear-gradient(90deg,#DCE6F2 1px,transparent 1px);
background-size:32px 32px;padding:46px 64px 130px;position:relative;overflow:hidden;display:flex;flex-direction:column}
main{flex:1;display:flex;flex-direction:column;justify-content:center}
.frame{position:absolute;inset:18px;border:2px solid #9FB3CC;pointer-events:none}
.tick{position:absolute;width:28px;height:28px;border-color:%(navy)s;border-style:solid}
h1{font-size:76px;font-weight:800;letter-spacing:-1px;text-align:center}
h2{font-size:38px;font-weight:500;text-align:center;margin-top:8px;color:#33415C}
.card{border:6px solid;border-radius:14px;overflow:hidden;box-shadow:6px 6px 0 rgba(20,33,61,.12);flex:1}
.card header{font-size:40px;font-weight:800;padding:16px 26px;border-bottom:6px solid;letter-spacing:1px}
.card .body{display:flex;gap:26px;align-items:flex-start;padding:24px 26px}
.card .body.stacked{flex-direction:column;gap:18px}
.card .body.stacked .icon{width:80px;height:80px}
.card .body.stacked li{font-size:33px}
.icon{width:96px;height:96px;flex:none}
ul{list-style:none;display:flex;flex-direction:column;gap:18px;border-left:6px solid;padding-left:22px}
li{font-size:36px;font-weight:600;line-height:1.15;display:flex;gap:16px;align-items:flex-start}
.dot{width:16px;height:16px;border-radius:50%%;flex:none;margin-top:.42em}
.arrow{width:120px;height:60px;flex:none}
footer{position:absolute;left:0;right:0;bottom:0;height:104px;background:#FFFFFF;border-top:4px solid %(navy)s;
display:flex;align-items:center;justify-content:space-between;padding:0 64px;font-size:30px}
.start{font-weight:800;font-size:34px}
.key{display:flex;gap:28px;align-items:center}
.key span{display:flex;gap:10px;align-items:center;font-weight:600}
.key i{width:26px;height:26px;display:inline-block;border:2px solid %(navy)s}
.note{color:#4A5674;font-size:26px}
""" % {"navy": NAVY}


def draw(brief: dict) -> str:
    ps = panels(brief)
    lines = {ln["role"]: ln["text"] for ln in brief["lines"] if ln["role"] in ("headline", "subtitle", "footer", "note")}
    legends = [ln["text"] for ln in brief["lines"] if ln["role"] == "legend"]
    legend_tone = {"Problem": "problem", "Change": "change", "Part": "part", "Proof": "proof", "Context": "context"}
    if brief["layout"] == "binary-comparison":
        left, right, proof = ps[0], ps[1:-1], ps[-1]
        middle = (
            "<div style='display:flex;align-items:center;gap:28px'>"
            f"<div style='flex:1'>{card(left)}</div>"
            "<div style='display:flex;flex-direction:column;align-items:center;align-self:stretch;justify-content:center'>"
            f"<div style='width:6px;flex:1;background:{NAVY};opacity:.25'></div>{arrow()}"
            f"<div style='width:6px;flex:1;background:{NAVY};opacity:.25'></div></div>"
            f"<div style='flex:1;display:flex;flex-direction:column;gap:20px'>{''.join(card(p) for p in right)}</div></div>"
            f"<div style='margin-top:30px'>{card(proof)}</div>"
        )
    else:
        parts = []
        stacked = len(ps) > 3
        for i, p in enumerate(ps):
            parts.append(f"<div style='flex:1;min-width:0;align-self:stretch;display:flex'>{card(p, stacked)}</div>")
            if i < len(ps) - 1:
                parts.append(f"<div style='align-self:center'>{arrow()}</div>")
        middle = f"<div style='display:flex;align-items:stretch;gap:14px'>{''.join(parts)}</div>"
    key = "".join(
        f"<span><i style='background:{TONES[legend_tone[k]][0]}'></i>{html.escape(k)}</span>" for k in legends
    )
    ticks = "".join(
        f"<div class='tick' style='{pos}'></div>"
        for pos in (
            "top:10px;left:10px;border-width:4px 0 0 4px",
            "top:10px;right:10px;border-width:4px 4px 0 0",
            "bottom:10px;left:10px;border-width:0 0 4px 4px",
            "bottom:10px;right:10px;border-width:0 4px 4px 0",
        )
    )
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
        f"<div class='frame'></div>{ticks}"
        f"<h1>{html.escape(lines['headline'])}</h1><h2>{html.escape(lines['subtitle'])}</h2><main>{middle}</main>"
        f"<footer><span class='start'>{html.escape(lines['footer'])}</span><span class='key'>{key}</span>"
        f"<span class='note'>{html.escape(lines['note'])}</span></footer></body></html>"
    )


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        for sid in sys.argv[1:]:
            d = R / "infographics" / sid
            brief = json.loads((d / "brief.json").read_text())
            (d / "infographic.html").write_text(draw(brief))
            page.goto((d / "infographic.html").as_uri())
            page.screenshot(path=str(d / "candidate-01.png"))
            (d / "provenance.json").write_text(json.dumps({
                "skill": "baoyu-infographic",
                "backend": "agent-drawn: html with inline svg written by claude-opus-5-5, rendered by headless chrome",
                "source": "infographic.html",
                "step1_failure": "429 usage_limit_reached: Codex main account blocked by main-account quota policy",
                "user_approval": "the fallback generation should still use baoyu-infographic skill",
                "prompt": "prompt.md",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2) + "\n")  # fmt: skip
            print(sid, d / "candidate-01.png", flush=True)
        browser.close()


if __name__ == "__main__":
    main()

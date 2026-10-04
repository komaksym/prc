"""Trusted HTML template. Every source-derived string passes through ``esc``; no scripts, no styles from source."""

from __future__ import annotations

from html import escape

from prc.presentation.doc import ClaimView, ConceptView, PresentationDoc
from prc.presentation.render_svg import STATE_LABEL
from prc.presentation.urlpolicy import anchor_for

CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
CSS = (
    "body{font-family:system-ui,sans-serif;margin:0 auto;max-width:960px;padding:16px;line-height:1.45}"
    "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd;padding:4px 8px;text-align:left}"
    ".banner{background:#fff3cd;border:1px solid #d9b100;padding:8px;margin:8px 0}"
    ".st-supported{border-left:6px solid #2a8a4a}.st-inference{border-left:6px solid #c9a100}"
    ".st-uncertainty{border-left:6px solid #d8741a}.st-gap{border-left:6px solid #c22}"
    ".st-agent_report{border-left:6px solid #55c}.claim{margin:6px 0;padding:4px 8px}"
    "pre{white-space:pre-wrap;word-break:break-word;background:#f5f5f8;padding:8px;overflow:auto}"
    ".meta{color:#445;font-size:.85em}"
)


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def _claim(claim: ClaimView) -> str:
    basis = {
        "mechanical": "mechanically checked",
        "model_assessed": "model assessed (fallible)",
        "none": "no support basis",
    }[claim.basis]
    links = []

    for link in claim.evidence:
        label = esc(link.record_id)
        links.append(f'<a href="#{link.anchor}">{label}</a>')

        if link.url is not None:
            links.append(f'<a href="{esc(link.url)}" rel="noopener noreferrer nofollow">GitHub</a>')

    notes = "".join(f"<li>{esc(item)}</li>" for item in claim.limitations)
    reason = (
        f"<p class='meta'>downgraded: {esc(claim.downgrade_reason)}</p>"
        if claim.downgrade_reason
        else ""
    )
    disagreement = "<p class='meta'>assessors disagreed</p>" if claim.disagreement else ""

    return (
        f'<div class="claim st-{claim.state}" id="{anchor_for("claim:" + claim.assertion_id)}">'
        f"<strong>{esc(STATE_LABEL[claim.state])}</strong> · {esc(basis)} · {esc(claim.kind)}"
        f"<div>{esc(claim.text)}</div>"
        f"<div class='meta'>evidence: {' '.join(links) if links else 'none'}</div>"
        f"<ul class='meta'>{notes}</ul>{reason}{disagreement}</div>"
    )


def _concept(view: ConceptView) -> str:
    relevance = "unranked" if view.relevance is None else f"decision relevance {view.relevance}"

    return (
        f"<section><h3>{esc(view.title)}</h3><p class='meta'>{esc(relevance)} · {esc(view.summary)}</p>"
        + "".join(_claim(claim) for claim in view.claims)
        + "</section>"
    )


def render_html(
    doc: PresentationDoc, infographic_svg: str, flow_svg: str | None, entry_link: str
) -> str:
    banner = (
        "<div class='banner'>FIXTURE DATA: deterministic local fixture, not a live GitHub "
        "observation.</div>"
        if doc.source_label == "fixture" or not doc.live_verified
        else ""
    )
    capture = (
        "<div class='banner'>Capture consistency is UNKNOWN: this bundle is not observed-fresh "
        "and cannot enter scored evaluation.</div>"
        if doc.consistency == "unknown"
        else ""
    )
    inventory = "".join(
        f"<tr><td>{esc(row.path)}</td><td>{esc(row.status)}</td><td>{esc(row.surface)}</td>"
        f"<td>{esc(row.lines)}</td><td>{esc(row.coverage)}</td></tr>"
        for row in doc.inventory
    )
    gaps = (
        "".join(
            f"<li><strong>{esc(gap.kind)}</strong> {esc(gap.subject)}: {esc(gap.reason)}</li>"
            for gap in doc.gaps
        )
        or "<li>none recorded</li>"
    )
    trace = (
        "<h2>Agent trace (reports, not proof)</h2>"
        + "".join(
            f"<details><summary>step {esc(event.step)} · {esc(event.tool)}</summary>"
            f"<p>{esc(event.summary)}</p></details>"
            for event in doc.trace
        )
        if doc.trace
        else ""
    )
    flow = f"<h2>Relation flow</h2>{flow_svg}" if flow_svg else ""
    excerpts = "".join(
        f'<details id="{esc(excerpt.anchor)}"><summary>{esc(excerpt.record_id)}</summary>'
        f"<pre>{esc(excerpt.text)}</pre></details>"
        for excerpt in doc.excerpts
    )
    models = "".join(
        f"<li>{esc(model.role)}: {esc(model.label)} {esc(model.version)}"
        f"{' (fixture)' if model.fixture else ''}</li>"
        for model in doc.models
    )

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{esc(CSP)}\">"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Review: {esc(doc.title)}</title><style>{CSS}</style></head><body>"
        f"<h1>{esc(doc.title)}</h1>{banner}{capture}"
        f"<p class='meta'>{esc(doc.pr_key)} · snapshot {esc(doc.snapshot_id)}<br>"
        f"semantic {esc(doc.semantic_id)}<br>Freshness is reconciled at presentation time with "
        f"<code>prc status</code>; this page is pinned and never claims to be current. "
        f"The human reviewer owns approve, reject or request changes.</p>"
        f"<h2>Overview</h2>{''.join(f'<p>{esc(line)}</p>' for line in doc.prose)}"
        f"<h2>Infographic</h2>{infographic_svg}{flow}"
        f"<h2>Concepts</h2>{''.join(_concept(view) for view in doc.concepts)}"
        f"<h2>Change surface</h2><table><tr><th>path</th><th>status</th><th>surface</th>"
        f"<th>lines</th><th>coverage</th></tr>{inventory}</table>"
        f"<h2>Coverage gaps</h2><ul>{gaps}</ul>{trace}"
        f"<h2>Evidence excerpts</h2>{excerpts}"
        f"<h2>Models</h2><ul>{models}</ul><p class='meta'>Entry: {esc(entry_link)}</p>"
        "</body></html>"
    )

from __future__ import annotations

import base64
import hashlib
import json
from importlib.resources import files
from typing import Any

from prc.changemap import ChangeMap
from prc.facts import compute_facts
from prc.identity import to_jsonable
from prc.presentation.graphdoc import groups_of, picked_steps, to_graph_doc

BRAND = "PR map \u00b7 computed from the code, no AI drew this"
_ASSETS = files("prc.presentation") / "map_assets"
_ESCAPES = str.maketrans(
    {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", "\u2028": "\\u2028", "\u2029": "\\u2029"}
)
_LEGEND = (
    '<div class="legend" aria-label="Legend">'
    '<div class="legend-row"><span class="sw st-added"></span>added'
    '<span class="sw st-modified"></span>modified<span class="sw st-deleted"></span>deleted'
    '<span class="sw st-context"></span>unchanged</div>'
    '<div class="legend-row"><svg class="ls" viewBox="0 0 40 8" aria-hidden="true">'
    '<path class="sample added" d="M2 4H38"/></svg>new call'
    '<svg class="ls" viewBox="0 0 40 8" aria-hidden="true"><path class="sample removed" d="M2 4H38"/>'
    "</svg>removed call"
    '<svg class="ls" viewBox="0 0 40 8" aria-hidden="true"><path class="sample kept" d="M2 4H38"/>'
    "</svg>call</div>"
    '<div class="legend-row"><svg class="ls" viewBox="0 0 40 8" aria-hidden="true">'
    '<path class="sample name" d="M2 4H38"/></svg>name-only: matched by name, '
    "no import proves it</div></div>"
)
_BODY = (
    '<div class="app"><header class="top"><div class="headline">'
    '<div class="eyebrow"><span class="logo" aria-hidden="true"><i></i><i></i><i></i></span>'
    '<span class="brand-name">PR map</span><span id="meta" class="meta"></span></div>'
    '<h1 id="title"></h1></div><div id="stats" class="stats"></div>'
    '<button id="play" class="play" type="button"><span class="play-icon" aria-hidden="true">'
    '</span><span id="play-label">Play tour</span></button></header>'
    '<main id="viewport" class="viewport"><div id="world" class="world"></div>'
    '<div class="spot" aria-hidden="true"></div>'
    '<div id="progress" class="progress" aria-hidden="true"><div id="progress-bar"></div></div>'
    '<div id="caption" class="caption" aria-live="polite"></div>'
    '<div id="summary" class="summary"></div>'
    f"{_LEGEND}"
    '<div class="zoom"><button id="zoom-in" type="button" aria-label="Zoom in">+</button>'
    '<button id="zoom-out" type="button" aria-label="Zoom out">\u2212</button>'
    '<button id="zoom-fit" type="button">Fit</button></div>'
    '<aside id="drawer" class="drawer" aria-hidden="true"></aside></main>'
    f'<footer class="foot"><span class="brand-line">{BRAND}</span>'
    '<span id="graph-coverage" class="graph-coverage"></span>'
    '<span class="hints">Click a node for its diff \u00b7 Drag to pan, pinch or Ctrl+scroll to zoom '
    "\u00b7 Space steps the tour \u00b7 F fits</span></footer></div>"
)


def page_data(change_map: ChangeMap) -> dict[str, Any]:
    """One JSON block: the stored map, the GraphDoc, the tour kinds, drop counts, groups."""
    data = to_jsonable(change_map)
    data["summary"] = to_jsonable(compute_facts(data))
    error = None
    try:
        plotted = to_graph_doc(change_map)
    except ValueError as issue:
        graph: dict[str, Any] | None = None
        dropped = {"symbols": len(change_map.symbols), "edges": len(change_map.edges)}
        error = str(issue)
    else:
        graph = plotted.doc
        dropped = {"symbols": plotted.dropped_symbols, "edges": plotted.dropped_edges}
    steps: list[dict[str, Any]] = []
    tour = picked_steps(change_map)
    for n, step in enumerate(tour):
        if step is None:
            steps.append({"kind": "overview" if n == 0 else "summary", "via": None})
        else:
            steps.append({"kind": step.kind, "via": step.via})
    groups = [
        {
            "id": "g" + str(n),
            "label": group.label,
            "is_dir": group.is_dir,
            "members": list(group.members),
            "added": group.added,
            "modified": group.modified,
            "deleted": group.deleted,
            "tests": group.tests,
        }
        for n, group in enumerate(groups_of(change_map))
    ]
    data["groups"] = groups
    result = {"map": data, "graph": graph, "steps": steps, "dropped": dropped}
    if error is not None:
        result["layoutError"] = error
    return result


def data_block(change_map: ChangeMap) -> str:
    """The page data as JSON that cannot close its script element or break a line terminator."""
    text = json.dumps(
        page_data(change_map), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return text.translate(_ESCAPES)


def render_map(change_map: ChangeMap) -> str:
    raw = (_ASSETS / "prlens.bundle.js").read_bytes()
    lock = json.loads((_ASSETS / "prlens.lock.json").read_text())
    if hashlib.sha256(raw).hexdigest() != lock["bundle_sha256"]:
        raise ValueError("PR Lens bundle hash does not match prlens.lock.json")
    bundle = raw.decode("utf-8")
    player = (_ASSETS / "map.js").read_text()
    bundle_digest = base64.b64encode(hashlib.sha256(raw).digest()).decode()
    player_digest = base64.b64encode(hashlib.sha256(player.encode()).digest()).decode()
    csp = (
        f"default-src 'none'; script-src 'sha256-{bundle_digest}' 'sha256-{player_digest}'; "
        "style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="dark light"><meta name="referrer" content="no-referrer">'
        '<link rel="icon" href="data:,">'
        f"<title>PR map</title><style>{(_ASSETS / 'map.css').read_text()}</style></head><body>{_BODY}"
        f'<script type="application/json" id="map-data">{data_block(change_map)}</script>'
        f"<script>{bundle}</script><script>{player}</script></body></html>\n"
    )

"""The PR map page: trusted markup, one JSON data block, one inline script allowed by hash.

PR-controlled strings reach the page only through the data block; the script builds DOM from it
with textContent and fixed attribute names.
"""

from __future__ import annotations

import base64
import hashlib
import json
from importlib.resources import files

from prc.changemap import ChangeMap
from prc.identity import to_jsonable
from prc.presentation.map_layout import (
    Box,
    Layout,
    MAIN,
    folder_edges,
    folders_of,
    layout_map,
    path_data,
)

BRAND = "PR map · computed from the code, no AI drew this"
_ASSETS = files("prc.presentation") / "map_assets"
_ESCAPES = str.maketrans(
    {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", " ": "\\u2028", " ": "\\u2029"}
)
_LEGEND = (
    '<div class="legend" aria-label="Legend">'
    '<div class="legend-row"><span class="sw st-added"></span>added'
    '<span class="sw st-modified"></span>modified<span class="sw st-deleted"></span>deleted'
    '<span class="sw st-context"></span>unchanged</div>'
    '<div class="legend-row"><svg class="ls" viewBox="0 0 40 8" aria-hidden="true">'
    '<path class="e e-added" d="M2 4H38"/></svg>new call'
    '<svg class="ls" viewBox="0 0 40 8" aria-hidden="true"><path class="e e-removed" d="M2 4H38"/>'
    "</svg>removed call"
    '<svg class="ls" viewBox="0 0 40 8" aria-hidden="true"><path class="e e-kept" d="M2 4H38"/>'
    "</svg>call</div>"
    '<div class="legend-row"><svg class="ls" viewBox="0 0 40 8" aria-hidden="true">'
    '<path class="e e-kept e-name" d="M2 4H38"/></svg>dotted: matched by name only, '
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
    '<button id="zoom-out" type="button" aria-label="Zoom out">−</button>'
    '<button id="zoom-fit" type="button">Fit</button></div>'
    '<aside id="drawer" class="drawer" aria-hidden="true"></aside></main>'
    f'<footer class="foot"><span class="brand-line">{BRAND}</span>'
    '<span class="hints">Click a node for its diff · Drag to pan, pinch or Ctrl+scroll to zoom '
    "· Space steps the tour · F fits</span></footer></div>"
)


def data_block(change_map: ChangeMap) -> str:
    """The map as JSON that cannot close its script element or break a line terminator."""

    text = json.dumps(
        to_jsonable(change_map), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )

    return text.translate(_ESCAPES)


def _box(box: Box) -> list[object]:
    return [box.lane, box.x, box.y, box.w, box.h]


def layout_json(change_map: ChangeMap, layout: Layout) -> str:
    """Geometry keyed by position in the map, so the script carries numbers and lane names only."""

    symbols: list[list[object] | None] = [None] * len(change_map.symbols)
    chips: list[list[object] | None] = [None] * len(change_map.files)
    symbol_at = {s.id: i for i, s in reversed(list(enumerate(change_map.symbols)))}
    file_at = {f.path: i for i, f in reversed(list(enumerate(change_map.files)))}

    groups: list[list[object]] = []

    for box in layout.boxes:
        if box.kind == "symbol":
            symbols[symbol_at[box.id]] = _box(box)
        elif box.kind == "group" and box.lane in MAIN:
            groups.append([*_box(box), symbol_at[box.id]])
        elif box.kind == "file":
            chips[file_at[box.id]] = _box(box)

    folders = folders_of(change_map)
    folder_box = {box.id: _box(box) for box in layout.boxes if box.lane == "folders"}
    route = {(r.source, r.target): path_data(r.points) for r in layout.routes}

    return json.dumps(
        {
            "w": layout.width,
            "h": layout.height,
            "bands": [[b.lane, b.x, b.y, b.w, b.h] for b in layout.bands],
            "symbols": symbols,
            "files": chips,
            "groups": groups,
            "dense": layout.dense,
            "edges": [route.get((e.source, e.target)) for e in change_map.edges],
            "folders": [folder_box[f.id] for f in folders],
            "folderInfo": [
                {
                    "label": f.label,
                    "is_dir": f.is_dir,
                    "added": f.added,
                    "modified": f.modified,
                    "deleted": f.deleted,
                    "tests": f.tests,
                    "members": [symbol_at[sid] for sid in f.members],
                }
                for f in folders
            ],
            "folderEdges": [
                [e.source, e.target, e.count, e.status]
                for e in folder_edges(change_map, folders)
            ],
        },
        separators=(",", ":"),
    )


def render_map(change_map: ChangeMap) -> str:
    css = (_ASSETS / "map.css").read_text()
    script = (
        f"const LAYOUT = {layout_json(change_map, layout_map(change_map))};\n"
        + (_ASSETS / "map.js").read_text()
    )
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    csp = (
        f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
        "img-src data:; base-uri 'none'; form-action 'none'"
    )

    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="dark light"><meta name="referrer" content="no-referrer">'
        '<link rel="icon" href="data:,">'
        f"<title>PR map</title><style>{css}</style></head><body>{_BODY}"
        f'<script type="application/json" id="map-data">{data_block(change_map)}</script>'
        f"<script>{script}</script></body></html>\n"
    )

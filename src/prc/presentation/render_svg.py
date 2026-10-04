"""Trusted SVG templates. Source text only enters as escaped text nodes; geometry is fixed."""

from __future__ import annotations

from xml.sax.saxutils import escape

from prc.presentation.doc import EdgeView, Infographic, InfographicNode

NODE_W = 300
NODE_H = 96
GAP_Y = 36
MARGIN = 24
STATE_CLASS = {
    "supported": "st-supported",
    "agent_report": "st-agent",
    "inference": "st-inference",
    "uncertainty": "st-uncertain",
    "gap": "st-gap",
}
STATE_LABEL = {
    "supported": "supported",
    "agent_report": "agent report",
    "inference": "inference",
    "uncertainty": "uncertain",
    "gap": "gap",
    "none": "no grouping claim",
}
SVG_STYLE = (
    ".node{fill:#fff;stroke:#334;stroke-width:1.5}.emph{stroke-width:4}"
    ".st-supported{fill:#e7f6ec}.st-agent{fill:#eef0ff}.st-inference{fill:#fff6dd}"
    ".st-uncertain{fill:#ffe9d6}.st-gap{fill:#fde0e0}text{font-family:sans-serif;font-size:13px;fill:#111}"
    ".small{font-size:11px;fill:#445}.edge{stroke:#334;stroke-width:2;fill:none}.dashed{stroke-dasharray:6 4}"
)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _text(x: int, y: int, value: str, css: str = "") -> str:
    klass = f' class="{css}"' if css else ""

    return f'<text x="{x}" y="{y}"{klass}>{escape(value)}</text>'


def _node(node: InfographicNode, row: int) -> str:
    y = MARGIN + row * (NODE_H + GAP_Y)
    classes = f"node {STATE_CLASS[node.worst_state]}" + (" emph" if node.emphasized else "")
    relevance = "unranked" if node.relevance is None else f"relevance {node.relevance}"
    grouping = "grouping: " + STATE_LABEL[node.group_state]
    marker = "most decision-relevant · " if node.emphasized else ""

    return "".join(
        [
            f'<g id="n{row}"><title>{escape(node.title)}</title>',
            f'<rect class="{classes}" x="{MARGIN}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="8" ry="8"/>',
            _text(MARGIN + 12, y + 24, _clip(node.title, 38)),
            _text(MARGIN + 12, y + 46, f"{marker}{relevance}", "small"),
            _text(
                MARGIN + 12,
                y + 64,
                f"least certain claim: {STATE_LABEL[node.worst_state]}",
                "small",
            ),
            _text(MARGIN + 12, y + 82, f"{grouping} · {node.claim_count} claims", "small"),
            "</g>",
        ]
    )


def _edge(edge: EdgeView, rows: dict[str, int]) -> str:
    source_row, target_row = rows[edge.source], rows[edge.target]
    source_y = MARGIN + source_row * (NODE_H + GAP_Y) + NODE_H // 2
    target_y = MARGIN + target_row * (NODE_H + GAP_Y) + NODE_H // 2
    bend_x = MARGIN + NODE_W + 60 + 14 * abs(source_row - target_row)
    start_x = MARGIN + NODE_W
    path = (
        f"M{start_x} {source_y} L{bend_x} {source_y} L{bend_x} {target_y} L{start_x + 6} {target_y}"
    )
    dashed = " dashed" if edge.state == "inference" else ""
    label = f"{edge.source} → {edge.target} ({STATE_LABEL[edge.state]})"

    return (
        f'<g><title>{escape(edge.text)}</title><path class="edge{dashed}" d="{path}" marker-end="url(#arrow)"/>'
        + _text(bend_x + 6, (source_y + target_y) // 2, _clip(label, 40), "small")
        + "</g>"
    )


def render_infographic(infographic: Infographic) -> str:
    """One row per concept in decision-relevance order; edges follow validated relations only."""

    rows = {node.concept_id: row for row, node in enumerate(infographic.nodes)}
    height = MARGIN * 2 + max(1, len(rows)) * (NODE_H + GAP_Y)
    width = MARGIN * 2 + NODE_W + 360
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="Change infographic">',
        f"<title>Change infographic</title><style>{SVG_STYLE}</style>",
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0 0 L6 3 L0 6 z" fill="#334"/></marker></defs>',
    ]
    parts.extend(_node(node, row) for row, node in enumerate(infographic.nodes))
    parts.extend(_edge(edge, rows) for edge in infographic.edges)
    parts.append("</svg>")

    return "".join(parts)


def render_flow(infographic: Infographic) -> str | None:
    """Flow diagram of validated relations; omitted when there are none."""

    if not infographic.edges:
        return None

    titles = {node.concept_id: node.title for node in infographic.nodes}
    height = MARGIN * 2 + len(infographic.edges) * 70
    width = 760
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="Relation flow">',
        f"<title>Relation flow</title><style>{SVG_STYLE}</style>",
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0 0 L6 3 L0 6 z" fill="#334"/></marker></defs>',
    ]

    for row, edge in enumerate(infographic.edges):
        y = MARGIN + row * 70
        dashed = " dashed" if edge.state == "inference" else ""
        parts.append(
            f"<g><title>{escape(edge.text)}</title>"
            f'<rect class="node {STATE_CLASS[edge.state]}" x="{MARGIN}" y="{y}" width="260" height="44" rx="6"/>'
            + _text(MARGIN + 10, y + 27, _clip(titles[edge.source], 30))
            + f'<path class="edge{dashed}" d="M{MARGIN + 260} {y + 22} L{width - 300} {y + 22}" marker-end="url(#arrow)"/>'
            + f'<rect class="node {STATE_CLASS[edge.state]}" x="{width - 294}" y="{y}" width="260" height="44" rx="6"/>'
            + _text(width - 284, y + 27, _clip(titles[edge.target], 30))
            + _text(MARGIN + 280, y + 16, STATE_LABEL[edge.state], "small")
            + "</g>"
        )

    parts.append("</svg>")

    return "".join(parts)

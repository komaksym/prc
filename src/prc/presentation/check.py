"""Pre-publication checks: semantic-operator preservation and output-structure allowlists."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from prc.presentation.doc import PresentationDoc
from prc.presentation.render_html import CSP, CSS
from prc.presentation.render_svg import SVG_STYLE
from prc.presentation.urlpolicy import is_allowed_href
from prc.semantics import ValidatedSemanticArtifact

SVG_NS = "http://www.w3.org/2000/svg"
HTML_TAGS = {
    "html", "head", "meta", "title", "style", "body", "h1", "h2", "h3", "p", "div", "section",
    "span", "strong", "code", "pre", "ul", "li", "a", "table", "tr", "td", "th", "details",
    "summary", "br",
}  # fmt: skip
SVG_TAGS = {"svg", "g", "rect", "text", "path", "defs", "marker", "title", "style"}
ATTRS = {
    "lang", "charset", "http-equiv", "content", "name", "class", "id", "href", "rel", "open",
    "width", "height", "viewbox", "x", "y", "rx", "ry", "d", "fill", "marker-end", "markerwidth",
    "markerheight", "refx", "refy", "orient", "role", "aria-label", "xmlns",
}  # fmt: skip
ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
TRUSTED_STYLES = {CSS, SVG_STYLE}
ALLOWED_META_CONTENT = {CSP, "width=device-width,initial-scale=1"}
ACTIVE = ("javascript:", "data:", "url(", "http:", "https:", "vbscript:", "expression(")


class PresentationError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems[:5]))
        self.problems = problems


EXACT_VALUES = {"xmlns": {SVG_NS}, "marker-end": {"url(#arrow)"}}
FREE_TEXT_ATTRS = {"content", "aria-label", "name", "class", "d"}


def _attribute_problem(tag: str, name: str, value: str) -> str | None:
    lowered = value.lower()

    if name not in ATTRS:
        return f"attribute {name!r} on <{tag}> is not allowed"

    if name == "href":
        return None if is_allowed_href(value) else f"href {value[:60]!r} violates URL policy"

    if name == "id":
        return None if ID_PATTERN.match(value) else f"id {value[:30]!r} is not a safe identifier"

    if name in EXACT_VALUES:
        return None if value in EXACT_VALUES[name] else f"{name} is not a trusted constant"

    if name == "content" and tag == "meta":
        return None if value in ALLOWED_META_CONTENT else "meta content is not a trusted constant"

    if name == "fill":
        return None if re.fullmatch(r"#[0-9a-f]{3,6}|none", value) else "fill is not a plain color"

    blocked = ("javascript:", "url(", "expression(") if name in FREE_TEXT_ATTRS else ACTIVE

    return (
        f"attribute {name!r} carries an active value"
        if any(t in lowered for t in blocked)
        else None
    )


def check_attribute(tag: str, name: str, value: str, problems: list[str]) -> None:
    problem = _attribute_problem(tag, name.lower(), value)

    if problem is not None:
        problems.append(problem)


class _Checker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[str] = []
        self.csp_seen = 0
        self._style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in HTML_TAGS and tag not in SVG_TAGS:
            self.problems.append(f"tag <{tag}> is not allowed")

        self._style = tag == "style"

        for name, value in attrs:
            check_attribute(tag, name, value or "", self.problems)

            if tag == "meta" and name == "http-equiv":
                self.csp_seen += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        self._style = False

    def handle_data(self, data: str) -> None:
        if self._style and data not in TRUSTED_STYLES:
            self.problems.append("style block is not a trusted constant")


def check_html(markup: str) -> None:
    checker = _Checker()
    checker.feed(markup)
    checker.close()

    if checker.csp_seen != 1:
        checker.problems.append("exactly one trusted CSP meta is required")

    if checker.problems:
        raise PresentationError(checker.problems)


def check_svg(markup: str) -> None:
    problems: list[str] = []

    try:
        root = ET.fromstring(markup)
    except ET.ParseError as error:
        raise PresentationError([f"svg is not well-formed: {error}"]) from error

    for element in root.iter():
        tag = element.tag.removeprefix(f"{{{SVG_NS}}}")

        if tag not in SVG_TAGS:
            problems.append(f"svg element <{tag}> is not allowed")

        for name, value in element.attrib.items():
            check_attribute(tag, name, value, problems)

        if tag == "style" and (element.text or "") not in TRUSTED_STYLES:
            problems.append("svg style is not a trusted constant")

    if problems:
        raise PresentationError(problems)


def check_entry(markdown: str, link: str) -> None:
    stripped = markdown.replace(link, "")
    problems = [
        f"unescaped {token!r} in entry text"
        for token in ("<", "](", "http:", "https:", "javascript:")
        if token in re.sub(r"\\.", "", stripped)
    ]

    if problems:
        raise PresentationError(problems)


def check_document(doc: PresentationDoc, artifact: ValidatedSemanticArtifact) -> None:
    """Presentation may only restate validated semantics; any drift blocks publication."""

    by_id = {assertion.assertion_id: assertion for assertion in artifact.assertions}
    concepts = {concept.concept_id: concept for concept in artifact.concepts}
    problems: list[str] = []

    for view in doc.concepts:
        if view.concept_id not in concepts:
            problems.append(f"unknown concept {view.concept_id}")

        for claim in view.claims:
            source = by_id.get(claim.assertion_id)

            if source is None:
                problems.append(f"unknown assertion {claim.assertion_id}")
                continue

            if (claim.text, claim.state, claim.basis) != (source.text, source.state, source.basis):
                problems.append(
                    f"{claim.assertion_id} text, state or basis diverges from validation"
                )

            if source.basis == "model_assessed" and not claim.limitations:
                problems.append(f"{claim.assertion_id} lost its model-assessed limitation")

            if {link.record_id for link in claim.evidence} != {
                r.record_id for r in source.evidence
            }:
                problems.append(f"{claim.assertion_id} evidence links diverge")

    for edge in doc.infographic.edges:
        source = by_id.get(edge.assertion_id)

        if (
            source is None
            or source.kind != "relation"
            or source.relation != (edge.source, edge.target)
            or source.state not in ("supported", "inference")
            or edge.state != source.state
        ):
            problems.append(f"edge {edge.assertion_id} does not match its validated relation")

    node_ids = {node.concept_id for node in doc.infographic.nodes}

    if not node_ids <= set(concepts):
        problems.append("infographic node outside validated concepts")

    emphasis = doc.infographic.emphasis_assertion_id

    if emphasis is not None and (emphasis not in by_id or by_id[emphasis].kind != "emphasis"):
        problems.append("infographic emphasis is not a validated emphasis assertion")

    for node in doc.infographic.nodes:
        if node.emphasized and (
            emphasis is None or node.concept_id not in by_id[emphasis].subject_ids
        ):
            problems.append(f"node {node.concept_id} emphasized without a validated assertion")

    if problems:
        raise PresentationError(problems)

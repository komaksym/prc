from __future__ import annotations

import dataclasses
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from html.parser import HTMLParser

import pytest

from prc.capture import capture_bundle
from prc.controller import analyze, fixture_suite, semantic_artifact_id
from prc.fixture_source import FixtureSource
from prc.model import PrRef
from prc.pipeline import render_view
from prc.presentation.build import build_document
from prc.presentation.check import (
    PresentationError,
    check_document,
    check_entry,
    check_html,
    check_svg,
)
from prc.presentation.doc import PresentationDoc
from prc.presentation.render_entry import md_escape, render_entry
from prc.presentation.render_html import render_html
from prc.presentation.render_svg import render_flow, render_infographic
from prc.presentation.urlpolicy import github_blob_url, is_allowed_href
from prc.semantics import ValidatedSemanticArtifact
from prc.snapshot import Acquisition, build_snapshot
from prc.verification import EligibilityPolicy

from conftest import FakeClock

Make = Callable[[str], tuple[FixtureSource, PrRef]]
HOSTILE = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "</text><script>alert(1)</script>",
    "</title><svg onload=alert(1)>",
    "{{7*7}} ${7*7}",
    "background:url(http://evil.invalid/x)",
    "[click](javascript:alert(1)) ![i](http://evil.invalid/i.png)",
]


def prepare(
    make: Make, name: str, clock: FakeClock
) -> tuple[Acquisition, ValidatedSemanticArtifact, PresentationDoc]:
    source, ref = make(name)
    acquisition = build_snapshot(
        capture_bundle(source, ref, clock), "fixture", False, source.repo, EligibilityPolicy()
    )
    artifact = analyze(acquisition, fixture_suite())
    doc = build_document(acquisition, artifact, semantic_artifact_id(artifact))

    return acquisition, artifact, doc


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text = ""
        self.hrefs: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text += data

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.hrefs.extend(value or "" for name, value in attrs if name == "href")


def test_hostile_repository_renders_inert_everywhere(make_source: Make, clock: FakeClock) -> None:
    acquisition, artifact, doc = prepare(make_source, "hostile", clock)
    info = render_infographic(doc.infographic)
    flow = render_flow(doc.infographic)
    markup = render_html(doc, info, flow, "index.html")
    entry = render_entry(doc, "index.html")

    check_html(markup)
    check_svg(info)
    check_entry(entry, "index.html")

    parsed = _Text()
    parsed.feed(markup)

    assert doc.title in parsed.text
    assert "<script>" not in markup.replace("&lt;script&gt;", "")
    assert all(is_allowed_href(href) for href in parsed.hrefs)
    assert "onerror=" not in markup.replace("onerror=alert(1)&gt;", "")
    assert "<script" not in info
    assert "<" not in re.sub(r"\\.", "", entry)


@pytest.mark.parametrize("payload", HOSTILE)
def test_hostile_strings_in_every_text_slot_stay_text(
    payload: str, make_source: Make, clock: FakeClock
) -> None:
    _, _, doc = prepare(make_source, "basic", clock)
    concept = dataclasses.replace(doc.concepts[0], title=payload, summary=payload)
    node = dataclasses.replace(doc.infographic.nodes[0], title=payload)
    edges = tuple(dataclasses.replace(edge, text=payload) for edge in doc.infographic.edges)
    hostile = dataclasses.replace(
        doc,
        title=payload,
        concepts=(concept, *doc.concepts[1:]),
        infographic=dataclasses.replace(
            doc.infographic, nodes=(node, *doc.infographic.nodes[1:]), edges=edges
        ),
        inventory=tuple(dataclasses.replace(row, path=payload) for row in doc.inventory),
        gaps=(dataclasses.replace(doc.gaps[0], reason=payload),) if doc.gaps else (),
    )
    info = render_infographic(hostile.infographic)
    flow = render_flow(hostile.infographic)
    markup = render_html(hostile, info, flow, "index.html")

    check_html(markup)
    check_svg(info)

    if flow:
        check_svg(flow)

    ET.fromstring(info)
    assert payload not in info.replace(payload.replace("&", "&amp;").replace("<", "&lt;"), "")


@pytest.mark.parametrize(
    "markup",
    [
        "<html><body><script>1</script></body></html>",
        '<html><body><p onclick="x">a</p></body></html>',
        "<html><body><img src='x'></body></html>",
        '<html><body><a href="javascript:alert(1)">x</a></body></html>',
        '<html><body><a href="https://evil.invalid/">x</a></body></html>',
        "<html><body><iframe src='x'></iframe></body></html>",
        '<html><body><p style="background:url(x)">a</p></body></html>',
        "<html><body><style>body{}</style></body></html>",
        "<html><body><link rel='stylesheet' href='x'></body></html>",
    ],
)
def test_html_checker_rejects_active_content(markup: str) -> None:
    with pytest.raises(PresentationError):
        check_html(markup)


@pytest.mark.parametrize(
    "markup",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="http://evil.invalid/x"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><use href="#a"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" onload="x"/>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(http://evil.invalid)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(http://x)</style></svg>',
        "<svg",
    ],
)
def test_svg_checker_rejects_active_content(markup: str) -> None:
    with pytest.raises(PresentationError):
        check_svg(markup)


def test_url_policy() -> None:
    sha = "a" * 40

    assert (
        github_blob_url("o/r", sha, "src/a b.py")
        == f"https://github.com/o/r/blob/{sha}/src/a%20b.py"
    )
    assert is_allowed_href("#rec-0123456789ab")
    assert is_allowed_href(f"https://github.com/o/r/blob/{sha}/x.py")

    for bad in (
        "javascript:alert(1)",
        "http://github.com/x",
        "https://evil.invalid/",
        "//evil",
        "data:text/html,x",
    ):
        assert not is_allowed_href(bad)

    with pytest.raises(ValueError):
        github_blob_url("o/r", "notasha", "x")

    with pytest.raises(ValueError):
        github_blob_url("o/../r", sha, "x")


def test_entry_markdown_is_escaped(make_source: Make, clock: FakeClock) -> None:
    _, _, doc = prepare(make_source, "hostile", clock)
    entry = render_entry(doc, "index.html")

    check_entry(entry, "index.html")
    assert "<" not in md_escape("<img src=x>").replace("\\<", "")
    assert "](" not in entry.replace("\\]\\(", "")


def test_document_check_blocks_semantic_drift(make_source: Make, clock: FakeClock) -> None:
    _, artifact, doc = prepare(make_source, "basic", clock)
    check_document(doc, artifact)

    claim = doc.concepts[0].claims[0]
    upgraded = dataclasses.replace(
        claim, state="supported", basis="mechanical", text=claim.text + " !"
    )
    drifted = dataclasses.replace(
        doc,
        concepts=(
            dataclasses.replace(doc.concepts[0], claims=(upgraded, *doc.concepts[0].claims[1:])),
            *doc.concepts[1:],
        ),
    )

    with pytest.raises(PresentationError):
        check_document(drifted, artifact)


def test_document_check_blocks_reversed_edge_and_invented_emphasis(
    make_source: Make, clock: FakeClock
) -> None:
    _, artifact, doc = prepare(make_source, "basic", clock)
    edge = doc.infographic.edges[0]
    reversed_edge = dataclasses.replace(edge, source=edge.target, target=edge.source)
    wrong_direction = dataclasses.replace(
        doc, infographic=dataclasses.replace(doc.infographic, edges=(reversed_edge,))
    )
    fake_emphasis = dataclasses.replace(
        doc, infographic=dataclasses.replace(doc.infographic, emphasis_assertion_id="a:1")
    )

    for bad in (wrong_direction, fake_emphasis):
        with pytest.raises(PresentationError):
            check_document(bad, artifact)


def test_non_supported_claims_keep_visible_markers(make_source: Make, clock: FakeClock) -> None:
    _, artifact, doc = prepare(make_source, "gaps", clock)
    markup = render_html(
        doc, render_infographic(doc.infographic), render_flow(doc.infographic), "index.html"
    )

    assert (
        "uncertain" in markup
        and "model assessed (fallible)" in markup
        and "mechanically checked" in markup
    )
    assert "FIXTURE DATA" in markup
    assert any(a.state == "uncertainty" for a in artifact.assertions)


def test_relation_direction_survives_into_svg(make_source: Make, clock: FakeClock) -> None:
    _, artifact, doc = prepare(make_source, "basic", clock)
    relation = next(a for a in artifact.assertions if a.kind == "relation")
    flow = render_flow(doc.infographic)

    assert flow is not None and relation.relation == ("c:tests", "c:src")
    assert flow.index("Changes in tests") < flow.index("Changes in src")


def test_every_review_has_an_infographic(make_source: Make, clock: FakeClock) -> None:
    for name in ("basic", "hostile", "opaque", "gaps"):
        acquisition, artifact, _ = prepare(make_source, name, clock)
        view = render_view(acquisition, artifact, semantic_artifact_id(artifact))

        assert "infographic.svg" in view.files and "index.html" in view.files

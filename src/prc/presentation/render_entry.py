"""Small GitHub-facing entry text. Markdown metacharacters in source strings are escaped."""

from __future__ import annotations

import re

from prc.presentation.doc import PresentationDoc

_META = re.compile(r"([\\`*_{}\[\]<>()#+\-.!|~&@:/])")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


def md_escape(value: str) -> str:
    return _META.sub(r"\\\1", _CONTROL.sub(" ", value))[:200]


def render_entry(doc: PresentationDoc, review_link: str) -> str:
    top = next((view for view in doc.concepts if view.relevance is not None), None)
    lines = [
        f"# Review summary: {md_escape(doc.title)}",
        "",
        f"- Concepts: {len(doc.concepts)}",
        f"- Coverage gaps: {len(doc.gaps)}",
        f"- Capture consistency: {doc.consistency}",
    ]

    if top is not None:
        lines.append(f"- Most decision-relevant: {md_escape(top.title)}")

    if doc.source_label == "fixture":
        lines.append("- Source: FIXTURE data, not a live GitHub observation")

    lines.extend(["", f"Full review: {review_link}", ""])

    return "\n".join(lines)

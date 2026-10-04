"""Brief as one GitHub comment. Every PR-controlled string goes through `span`, nothing else."""

from __future__ import annotations

import re
import unicodedata

from prc.brief import Brief, FileChange, Kind, unnamed

MARKER = "<!-- prc-brief -->"
SPAN_LIMIT = 140
NOT_NAMED_SHOWN = 5
KIND_ORDER: tuple[Kind, ...] = ("code", "config", "test", "docs", "opaque")


def span(value: str) -> str:
    """The only door for untrusted text: one inline code span, single line, bounded."""

    flat = "".join(" " if unicodedata.category(ch).startswith("C") else ch for ch in value)
    text = re.sub(r"\s+", " ", flat.replace("`", "'")).strip()

    if len(text) > SPAN_LIMIT:
        text = text[: SPAN_LIMIT - 1].rstrip() + "…"

    return f"`{text}`"


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _size(files: tuple[FileChange, ...]) -> str:
    real = [f for f in files if f.kind != "generated"]
    generated = [f for f in files if f.kind == "generated"]
    kinds = ", ".join(
        f"{sum(1 for f in real if f.kind == kind)} {kind}"
        for kind in KIND_ORDER
        if any(f.kind == kind for f in real)
    )
    line = (
        f"**Size.** +{sum(f.added for f in real)} −{sum(f.removed for f in real)}"
        f" in {_count(len(real), 'file')}"
    )

    if kinds:
        line += f" ({kinds})"

    line += "."

    if generated:
        line += (
            f" Generated files, not counted above: {_count(len(generated), 'file')},"
            f" +{sum(f.added for f in generated)} −{sum(f.removed for f in generated)}."
        )

    return line


def _ci(brief: Brief) -> str:
    if not brief.checks:
        return "**CI on this commit.** No checks ran."

    parts = []

    for state, label in (("failed", "Failed"), ("pending", "Pending")):
        names = [c.name for c in brief.checks if c.state == state]

        if names:
            parts.append(f"{label}: {', '.join(span(n) for n in names)}.")

    passed = sum(1 for c in brief.checks if c.state == "passed")

    if passed:
        parts.append(f"Passed: {passed}.")

    return "**CI on this commit.** " + " ".join(parts)


def render_brief(brief: Brief) -> str:
    lines = [
        MARKER,
        "### PR brief",
        "",
        "Computed from the diff, the description and CI results. No AI-written text.",
        "",
        _size(brief.files),
        "",
        _ci(brief),
        "",
        "#### Description vs diff",
    ]

    if brief.mismatches:
        for m in brief.mismatches:
            subjects = ", ".join(span(s) for s in m.subjects)
            lines.append(f"- {span(m.quote)}")
            lines.append(f"  - {m.fact} {subjects}".rstrip())
    else:
        lines.append("Everything the description names is in the diff.")

    missing = unnamed(brief.files)

    if missing:
        lines += ["", "#### Not named in the description"]
        lines += [f"- {span(f.path)} (+{f.added} −{f.removed})" for f in missing[:NOT_NAMED_SHOWN]]

        if len(missing) > NOT_NAMED_SHOWN:
            lines.append(f"- and {len(missing) - NOT_NAMED_SHOWN} more")

    lines += ["", "#### Look here first"]

    if brief.look_first:
        for pointer in brief.look_first:
            lines.append(f"- {span(pointer.path)}: {pointer.reason}")
            lines.extend(f"  - added: {span(line)}" for line in pointer.lines)
    else:
        lines.append("Nothing stands out.")

    return "\n".join(lines) + "\n"

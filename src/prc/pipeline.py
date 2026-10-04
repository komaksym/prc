"""Controller orchestration: acquire, analyze, present, publish, reconcile, record."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from prc.capture import Clock, capture_bundle
from prc.controller import ModelSuite, analyze, semantic_artifact_id
from prc.freshness import FreshnessReport, StoredBasis, reconcile
from prc.identity import PublicationKey, SemanticArtifactId, content_id, sha256_hex, to_jsonable
from prc.model import PrRef
from prc.presentation.build import build_document
from prc.presentation.check import (
    check_document,
    check_entry,
    check_html,
    check_svg,
)
from prc.presentation.render_entry import render_entry
from prc.presentation.render_html import render_html
from prc.presentation.render_svg import render_flow, render_infographic
from prc.presentation.versions import PRESENTATION_POLICY_VERSION, RENDERER_VERSIONS
from prc.semantics import ValidatedSemanticArtifact
from prc.snapshot import Acquisition, build_snapshot
from prc.source import PullRequestSource
from prc.store import Store
from prc.verification import EligibilityPolicy

ENTRY_LINK = "index.html"


@dataclass(frozen=True, slots=True)
class RenderedView:
    view_id: str
    files: dict[str, bytes]
    hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class ReviewResult:
    snapshot_id: str
    semantic_id: str
    view_id: str
    won_canonicalization: bool
    consistency: str
    gap_count: int
    out_dir: Path
    files: tuple[str, ...]


def render_view(
    acquisition: Acquisition, artifact: ValidatedSemanticArtifact, semantic_id: SemanticArtifactId
) -> RenderedView:
    doc = build_document(acquisition, artifact, semantic_id)
    check_document(doc, artifact)
    infographic_svg = render_infographic(doc.infographic)
    flow_svg = render_flow(doc.infographic)
    markup = render_html(doc, infographic_svg, flow_svg, ENTRY_LINK)
    entry = render_entry(doc, ENTRY_LINK)

    for svg in (infographic_svg, flow_svg):
        if svg is not None:
            check_svg(svg)

    check_html(markup)
    check_entry(entry, ENTRY_LINK)
    files = {
        "index.html": markup.encode(),
        "infographic.svg": infographic_svg.encode(),
        "entry.md": entry.encode(),
    }

    if flow_svg is not None:
        files["flow.svg"] = flow_svg.encode()

    hashes = {name: sha256_hex(data) for name, data in sorted(files.items())}
    view_id = content_id(
        "published-view",
        {
            "semantic": semantic_id,
            "presentation_policy": PRESENTATION_POLICY_VERSION,
            "renderers": RENDERER_VERSIONS,
            "artifacts": hashes,
        },
    )

    return RenderedView(view_id, files, hashes)


def run_review(
    source: PullRequestSource,
    ref: PrRef,
    store: Store,
    suite: ModelSuite,
    clock: Clock,
    policy: EligibilityPolicy,
    out_root: Path,
) -> ReviewResult:
    bundle = capture_bundle(source, ref, clock)
    acquisition = build_snapshot(
        bundle, source.label, source.live_verified, source.repo_path(ref), policy
    )
    snapshot = acquisition.snapshot
    artifact = analyze(acquisition, suite)
    semantic_id = semantic_artifact_id(artifact)
    view = render_view(acquisition, artifact, semantic_id)
    key = PublicationKey(
        content_id(
            "publication",
            [snapshot.snapshot_id, snapshot.comprehension_version, snapshot.validation_version],
        )
    )
    supporting = {record_id: text.encode() for record_id, text in acquisition.records.items()}
    canonical_id, view_id, won = store.publish(
        pr_key=ref.key,
        snapshot_id=snapshot.snapshot_id,
        snapshot_body=snapshot,
        publication_key=key,
        semantic_id=semantic_id,
        semantic_body=artifact,
        view_id=view.view_id,
        files=view.files,
        supporting=supporting,
    )
    files = store.view_files(view_id)
    semantic = store.canonical_semantic(key)
    extras = {
        "snapshot.json": store.snapshot_body(snapshot.snapshot_id),
        "manifest.json": to_jsonable(acquisition.manifest),
        "semantic.json": semantic,
        "view.json": {
            "snapshot_id": snapshot.snapshot_id,
            "semantic_id": canonical_id,
            "view_id": view_id,
            "artifact_hashes": {name: sha256_hex(data) for name, data in sorted(files.items())},
            "source": {"label": source.label, "live_verified": source.live_verified},
        },
    }
    out_dir = _write_bundle(out_root, view_id, files, extras)

    return ReviewResult(
        snapshot.snapshot_id,
        canonical_id,
        view_id,
        won,
        snapshot.consistency,
        len(semantic["gaps"]),
        out_dir,
        tuple(sorted({*files, *extras})),
    )


def _write_bundle(
    out_root: Path, view_id: str, files: dict[str, bytes], extras: dict[str, object]
) -> Path:
    """Write into a temp dir and rename into place; a view's bundle is never partially visible."""

    out_dir = out_root / view_id.rsplit(":", 1)[-1][:16]

    if out_dir.exists():
        return out_dir

    out_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=out_root))

    for name, data in files.items():
        (staging / name).write_bytes(data)

    for name, body in extras.items():
        (staging / name).write_text(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False))

    try:
        staging.rename(out_dir)
    except OSError:
        shutil.rmtree(staging)

    return out_dir


def run_status(
    source: PullRequestSource,
    ref: PrRef,
    store: Store,
    policy: EligibilityPolicy,
    clock: Clock,
) -> tuple[str, str, FreshnessReport]:
    current = store.current(ref.key)

    if current is None:
        raise LookupError(f"no review recorded for {ref.key}")

    snapshot_id, view_id = current
    body = store.snapshot_body(snapshot_id)
    stored = StoredBasis(
        str(body["basis_id"]),
        {str(name): str(digest) for name, digest in body["basis_components"]},  # type: ignore[attr-defined]
    )

    return snapshot_id, view_id, reconcile(source, ref, stored, policy, clock)


def run_decide(
    source: PullRequestSource,
    ref: PrRef,
    store: Store,
    policy: EligibilityPolicy,
    clock: Clock,
    *,
    expected_snapshot_id: str,
    expected_view_id: str,
    reviewer: str,
    decision: str,
    confidence: int | None,
    note: str,
) -> tuple[int, FreshnessReport]:
    """Reconcile the full basis at the write boundary, then CAS-record the human decision."""

    _, _, report = run_status(source, ref, store, policy, clock)
    decision_id = store.record_decision(
        pr_key=ref.key,
        expected_snapshot_id=expected_snapshot_id,
        expected_view_id=expected_view_id,
        reviewer=reviewer,
        decision=decision,
        confidence=confidence,
        note=note,
        freshness=report,
    )

    return decision_id, report

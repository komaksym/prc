"""Controller orchestration: acquire, analyze, present, publish, reconcile, record."""

from __future__ import annotations

import dataclasses
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from prc.brief import Brief, build_brief
from prc.capture import Clock, capture_bundle
from prc.changemap import ChangeMap, build_change_map
from prc.controller import ModelSuite, analyze, semantic_artifact_id
from prc.explainer import render as explain_render
from prc.explainer.check import verify_board
from prc.explainer.doc import render_doc as render_explain_doc
from prc.explainer.timing import estimate as estimate_seconds
from prc.explainer.timing import predict as predict_seconds
from prc.explainer.voice import Backend
from prc.explainer.voice import select as select_voice
from prc.freshness import FreshnessReport, StoredBasis, reconcile
from prc.gitutil import list_paths
from prc.identity import PublicationKey, SemanticArtifactId, content_id, sha256_hex, to_jsonable
from prc.model import PrRef
from prc.presentation.build import build_document
from prc.presentation.card import CardError
from prc.presentation.card import build_card_html as build_pr_card_html
from prc.presentation.card import render_card_png as render_pr_card_png
from prc.presentation.check import (
    check_document,
    check_entry,
    check_html,
    check_svg,
)
from prc.presentation.comment import render_comment as render_pr_comment
from prc.presentation.render_brief import render_brief
from prc.presentation.render_entry import render_entry
from prc.presentation.render_html import render_html
from prc.presentation.render_map import render_map
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


@dataclass(frozen=True, slots=True)
class BriefResult:
    snapshot_id: str
    brief: Brief
    path: Path


def _acquire_brief(
    source: PullRequestSource, ref: PrRef, clock: Clock, policy: EligibilityPolicy
) -> tuple[Acquisition, Path, Brief]:
    bundle = capture_bundle(source, ref, clock)
    repo = source.repo_path(ref)
    acquisition = build_snapshot(bundle, source.label, source.live_verified, repo, policy)
    comparison = acquisition.snapshot.comparison
    known = frozenset(list_paths(repo, comparison.merge_base_sha)) | frozenset(
        list_paths(repo, comparison.head_sha)
    )

    return acquisition, repo, build_brief(acquisition, known)


def run_brief(
    source: PullRequestSource,
    ref: PrRef,
    clock: Clock,
    policy: EligibilityPolicy,
    out_root: Path,
) -> BriefResult:
    acquisition, _, brief = _acquire_brief(source, ref, clock, policy)
    snapshot_id = acquisition.snapshot.snapshot_id
    out_dir = _write_bundle(
        out_root,
        snapshot_id,
        {"brief.md": render_brief(brief).encode()},
        {"brief.json": to_jsonable(brief)},
        replace=True,
    )

    return BriefResult(snapshot_id, brief, out_dir / "brief.md")


@dataclass(frozen=True, slots=True)
class MapResult:
    snapshot_id: str
    map: ChangeMap
    html: Path
    json: Path


def run_map(
    source: PullRequestSource,
    ref: PrRef,
    clock: Clock,
    policy: EligibilityPolicy,
    out_root: Path,
) -> MapResult:
    acquisition, repo, brief = _acquire_brief(source, ref, clock, policy)
    url = f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}"
    change_map = dataclasses.replace(
        build_change_map(acquisition, repo, brief), url=url if source.live_verified else None
    )
    snapshot_id = acquisition.snapshot.snapshot_id
    out_dir = _write_bundle(
        out_root,
        snapshot_id,
        {"index.html": render_map(change_map).encode()},
        {"map.json": to_jsonable(change_map)},
        replace=True,
    )

    return MapResult(snapshot_id, change_map, out_dir / "index.html", out_dir / "map.json")


def _write_bundle(
    out_root: Path,
    view_id: str,
    files: dict[str, bytes],
    extras: dict[str, object],
    replace: bool = False,
) -> Path:
    out_dir = out_root / view_id.rsplit(":", 1)[-1][:16]

    if out_dir.exists() and not replace:
        return out_dir

    out_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=out_root))

    for name, data in files.items():
        (staging / name).write_bytes(data)

    for name, body in extras.items():
        (staging / name).write_text(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False))

    if replace:
        shutil.rmtree(out_dir, ignore_errors=True)

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


class ExplainCheckError(RuntimeError):
    """A board that failed the checker, one line per error."""


@dataclass(frozen=True, slots=True)
class ExplainResult:
    out_dir: Path
    map_json: Path
    map_html: Path
    board_json: Path | None
    video: Path | None
    doc_html: Path | None
    card_html: Path
    card_png: Path | None
    comment_md: Path
    run_json: Path
    duration: float
    estimate: float
    check_passed: bool


def _live_map_dict(
    source: PullRequestSource, ref: PrRef, clock: Clock, policy: EligibilityPolicy
) -> tuple[dict[str, object], ChangeMap, Path]:
    acquisition, repo, brief = _acquire_brief(source, ref, clock, policy)
    url = f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}"
    change_map = dataclasses.replace(
        build_change_map(acquisition, repo, brief), url=url if source.live_verified else None
    )

    return to_jsonable(change_map), change_map, repo


def explain_slug(ref: PrRef, head_sha: str) -> str:
    """One output folder per head: files from an older head never mix with a newer one."""
    return f"{ref.owner}-{ref.repo}-{ref.number}-{head_sha[:12]}"


def load_map_dict(
    source: PullRequestSource,
    ref: PrRef,
    clock: Clock,
    policy: EligibilityPolicy,
    map_path: Path | None = None,
) -> tuple[dict[str, object], dict[str, object], ChangeMap, Path]:
    """The map a board reads: the stored one when its head differs from live, else live."""
    live_dict, change_map, repo = _live_map_dict(source, ref, clock, policy)
    if map_path is None:
        return live_dict, live_dict, change_map, repo
    stored = json.loads(map_path.read_text())
    if stored["head_sha"] != live_dict["head_sha"]:
        return stored, live_dict, change_map, repo
    return live_dict, live_dict, change_map, repo


def run_explain(
    source: PullRequestSource,
    ref: PrRef,
    clock: Clock,
    policy: EligibilityPolicy,
    out_root: Path,
    board_path: Path | None = None,
    map_path: Path | None = None,
    voice: str = "auto",
    git_dir: str | None = None,
) -> ExplainResult:
    used, live_dict, change_map, repo = load_map_dict(source, ref, clock, policy, map_path)
    map_source = "stored" if used is not live_dict else "live"
    stored_head = used["head_sha"]

    backend: Backend = select_voice(voice)
    slug = explain_slug(ref, str(used["head_sha"]))
    out_dir = out_root / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "map.json").write_text(json.dumps(used, indent=2, sort_keys=True))
    (out_dir / "map.html").write_text(render_map(change_map))

    check_passed, board_out, video, doc_out, duration, estimate, predicted, warnings = (
        False,
        None,
        None,
        None,
        0.0,
        0.0,
        0.0,
        [],
    )
    check_detail: dict[str, object] = {"passed": False, "board": None}
    board: dict[str, Any] | None = None
    if board_path is not None:
        board = json.loads(board_path.read_text())
        try:
            facts = verify_board(board, used)
        except SystemExit as error:
            raise ExplainCheckError(str(error)) from error
        check_passed = True
        check_detail = {
            "passed": True,
            "receipts": facts["receipts"],
            "covered": facts["covered"],
            "changed": facts["changed"],
            "tests_added": facts["tests_added"],
        }
        estimate = estimate_seconds(board)
        board_out = out_dir / "board.json"
        board_out.write_text(json.dumps(board, indent=2, sort_keys=True))
        rendered = explain_render.render(
            board,
            used,
            facts,
            out_dir,
            backend,
            git_dir if git_dir is not None else (str(repo) if repo.exists() else None),
        )
        duration, warnings = rendered.duration, rendered.layout_warnings
        video = out_dir / "video.mp4"
        predicted = predict_seconds(board, backend)
        render_explain_doc(board, used, out_dir, duration, has_video=True)
        doc_out = out_dir / "doc.html"

    card_html = out_dir / "card.html"
    card_html.write_text(build_pr_card_html(cast("dict[str, Any]", used), board))
    card_png: Path | None = None
    try:
        render_pr_card_png(card_html, out_dir / "card.png")
        card_png = out_dir / "card.png"
    except CardError as error:
        warnings = [*warnings, str(error)]
    comment_md = out_dir / "comment.md"
    comment_md.write_text(render_pr_comment(cast("dict[str, Any]", used), board))

    run = {
        "source": source.label,
        "pr": used["pr"],
        "live_head_sha": live_dict["head_sha"],
        "stored_head_sha": stored_head,
        "map_source": map_source,
        "board": str(board_path) if board_path else None,
        "check": check_detail,
        "voice": backend.name,
        "estimate_seconds": round(estimate, 2),
        "predicted_seconds": round(predicted, 2),
        "duration_seconds": round(duration, 2),
        "fps": explain_render.FPS,
        "doc": str(doc_out) if doc_out else None,
        "card": str(card_png) if card_png else None,
        "comment": str(comment_md),
        "layout_warnings": warnings,
    }
    run_json = out_dir / "run.json"
    run_json.write_text(json.dumps(run, indent=2, sort_keys=True))

    return ExplainResult(
        out_dir,
        out_dir / "map.json",
        out_dir / "map.html",
        board_out,
        video,
        doc_out,
        card_html,
        card_png,
        comment_md,
        run_json,
        duration,
        estimate,
        check_passed,
    )

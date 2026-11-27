"""Paired-eval kit: manifest validation, sealing, blinded export, and grading."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prc.evaluation.protocol import (
    Pair,
    Protocol,
    SealedExperiment,
    assign,
    seal_digest,
    seal_experiment,
    verify_seal,
)


class KitError(ValueError):
    """Preparation, validation, export, or grading failure."""


SCHEMA_VERSION = 2
PRODUCT_TREATMENT_ID = "github+prc"
BASELINE_TREATMENT_ID = "github+lens-ci"
PACKET_POLICY = "use_assigned_tool_only"

EXPOSED_PR_IDS = frozenset(
    {"willtho89/librarySync#98", "cybersemics/em#5756", "swarm-deploy/swarm-deploy#116"}
)
LENS_APP_SLUGS = ("coldtea-pr-lens", "coldtea-pr-lens-action")
LENS_COMMENT_AUTHORS = ("coldtea-pr-lens[bot]", "github-actions[bot]")
LENS_STICKY_MARKER = "<!-- pr-lens:sticky -->"
LENS_STATE_MARKER_PREFIX = "<!-- pr-lens:state "

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_PR_IDENTITY = re.compile("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[0-9]+$")
_GITHUB_COMMENT_URL = re.compile(
    "^https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+#issuecomment-[0-9]+$"
)
_CONTENT_ADDRESSED = re.compile(r"^[0-9a-f]{32}\.svg$")
_QUESTION_ORDER = ("multiple_choice", "short", "short")
_MC_ANCHORS = (0.0, 1.0)
_SHORT_ANCHORS = (0.0, 0.5, 1.0)
_MAX_CHANGED_LINES = 500
_MAX_CHANGED_FILES = 10

_DEFAULT_PRC_INDEX = "index.html"


PAIRED_PROTOCOL_V2 = Protocol(
    pair_count=3,
    items_per_snapshot=3,
    multiple_choice_items=1,
    short_items=2,
    success_threshold_pp=10.0,
    bootstrap_resamples=20_000,
    bootstrap_seed=12024,
    generation_cap_seconds=0.0,
    deadline_seconds=1200.0,
    pairs_per_session=3,
    session_days=(1,),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise KitError(message)


def _require_str(value: Any, message: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", message)

    return str(value)


def _require_sha40(value: Any, message: str) -> str:
    _require(isinstance(value, str) and bool(_SHA40.match(value)), message)

    return str(value)


def _build_protocol(block: Mapping[str, Any], pair_count: int) -> Protocol:
    _require(
        int(block["pair_count"]) == pair_count,
        "protocol pair_count must equal the number of pairs",
    )
    per_session = int(block["pairs_per_session"])
    days = tuple(int(day) for day in block["session_days"])
    _require(len(days) * per_session >= pair_count, "session plan cannot cover all pairs")

    from dataclasses import replace

    return replace(
        PAIRED_PROTOCOL_V2,
        pair_count=pair_count,
        pairs_per_session=per_session,
        session_days=days,
    )


def _load_comment_body(lens_dir: Path, relative: str) -> str:
    path = lens_dir / relative
    _require(path.is_file(), f"lens comment file {relative} is missing")
    text = path.read_text()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text

    body = parsed.get("body") if isinstance(parsed, dict) else None

    return str(body) if body is not None else text


def _validate_lens_record(snap: Mapping[str, Any], lens_dir: Path) -> None:
    page = lens_dir / "index.html"
    _require(page.is_file(), "lens index.html is missing")
    spec = snap["lens"]
    page_pin = str(spec.get("page_sha256") or "")
    _require(bool(_SHA64.match(page_pin)), "lens page_sha256 must be recorded as 64 hex")
    _require(
        hashlib.sha256(page.read_bytes()).hexdigest() == page_pin,
        "lens page_sha256 does not match the captured index bytes",
    )
    head = snap["head_sha"]
    _require(int(spec["comment_id"]) > 0, "lens comment_id must be present")
    _require(
        bool(_GITHUB_COMMENT_URL.match(str(spec["comment_url"]))),
        "lens comment_url must be a github pull issuecomment URL",
    )
    comment_rel = _require_str(spec["comment_path"], "lens comment_path must be recorded")
    _artifact_path(lens_dir, comment_rel)
    body = _load_comment_body(lens_dir, comment_rel)
    _require(LENS_STICKY_MARKER in body, "lens comment is missing the sticky marker")
    _require(
        body.startswith(LENS_STATE_MARKER_PREFIX) or LENS_STATE_MARKER_PREFIX in body,
        "lens comment is missing the state marker",
    )
    marker = re.search(r"<!-- pr-lens:state (.*?) -->", body, re.DOTALL)
    _require(marker is not None, "lens comment state is malformed")
    assert marker is not None
    state = json.loads(marker.group(1))
    _require(state.get("headSha") == head, "lens comment state does not match the pinned head")
    _require(spec["headSha"] == head, "lens headSha must match the pinned head")

    author = _require_str(spec["comment_author"], "lens comment_author must be recorded")
    _require(author in LENS_COMMENT_AUTHORS, "lens comment author is not the lens bot identity")
    comment_json = json.loads((lens_dir / comment_rel).read_text())
    login = (comment_json.get("user") or {}).get("login")
    _require(login == author, "captured comment user.login does not match the manifest")
    captured_id = str(comment_json.get("id"))
    _require(
        captured_id == str(spec["comment_id"]), "captured comment id does not match the manifest"
    )

    run_rel = _require_str("check_run.json", "lens check record must be captured")
    run_path = lens_dir / run_rel
    _require(run_path.is_file(), "captured check_run.json is missing")
    record = json.loads(run_path.read_text())
    _require(
        str(record.get("id")) == str(spec["check_run_id"]),
        "captured check id does not match the manifest",
    )
    slug = ((record.get("app") or {}).get("slug")) or ""
    _require(
        str(spec["check_app_slug"]) == slug,
        "manifest check_app_slug does not match the captured app record",
    )
    _require(slug in LENS_APP_SLUGS, "captured check app slug is not the lens app")
    _require(record.get("head_sha") == head, "captured check head does not match the pinned head")
    _require(record.get("status") == "completed", "captured check run is not completed")
    _require(record.get("conclusion") == "success", "captured check run did not succeed")
    _require(spec["check_head_sha"] == head, "check_head_sha must equal the pinned head")
    _require(
        bool(_SHA40.match(str(spec["reviewed_sha"]))) and spec["reviewed_sha"] == head,
        "reviewed_sha must equal the pinned head",
    )
    graph_key = _require_str(spec["graphKey"], "graphKey must be recorded")
    _require(head in graph_key, "graphKey must contain the full pinned head")
    if state.get("graphKey") is not None:
        _require(state["graphKey"] == graph_key, "captured graphKey does not match the manifest")
    version = _require_str(spec["version"], "lens version must be recorded")
    _require(len(version) > 0, "lens version must be non-empty")

    svg_entries = spec["svg_files"]
    _require(
        isinstance(svg_entries, list) and len(svg_entries) > 0, "lens svg_files must be non-empty"
    )
    for entry in svg_entries:
        svg_rel = str(entry["path"])
        _require(
            bool(_CONTENT_ADDRESSED.match(Path(svg_rel).name)),
            "svg file names must be content-addressed",
        )
        svg_path = _artifact_path(lens_dir, svg_rel)
        _require(svg_path.is_file(), f"lens svg file {svg_rel} is missing")
        digest = hashlib.sha256(svg_path.read_bytes()).hexdigest()
        _require(
            Path(svg_rel).stem == digest[:32], "svg file name is not content-addressed to its bytes"
        )
        _require(digest == entry["sha256"], "svg sha256 does not match the captured bytes")
        _require(bool(_SHA64.match(str(entry["sha256"]))), "svg sha256 must be 64 hex")


def _validate_prc_record(snap: Mapping[str, Any], prc_dir: Path) -> None:
    spec = snap["prc"]
    _require(spec["base_sha"] == snap["base_sha"], "prc base_sha does not match the snapshot base")
    _require(spec["head_sha"] == snap["head_sha"], "prc head does not match the snapshot head")
    map_path = prc_dir / "map.json"
    _require(map_path.is_file(), "prc map.json is missing")
    actual_map = json.loads(map_path.read_text())
    _require(
        actual_map.get("base_sha") == snap["base_sha"], "prc map base differs from the pinned base"
    )
    _require(
        actual_map.get("head_sha") == snap["head_sha"], "prc map head differs from the pinned head"
    )
    index_rel = str(spec.get("index_path") or _DEFAULT_PRC_INDEX)
    index_path = _artifact_path(prc_dir, index_rel)
    _require(index_path.is_file(), "prc index.html is missing")
    index_bytes = index_path.read_bytes()
    _require(
        LENS_STICKY_MARKER not in index_bytes.decode("utf-8", "replace"),
        "prc artifact must not carry the lens sticky marker",
    )
    digest = hashlib.sha256(index_bytes).hexdigest()
    _require(
        digest == spec["output_hash"], "prc output_hash does not match the captured index bytes"
    )
    _require(bool(_SHA64.match(str(spec["output_hash"]))), "prc output_hash must be 64 hex")
    _require_str(spec["render_identity"], "prc render_identity must be recorded")


def _validate_questions(questions: Sequence[Mapping[str, Any]], snapshot_id: str) -> None:
    _require(len(questions) == 3, f"snapshot {snapshot_id} needs exactly three questions")
    kinds = tuple(str(q["kind"]) for q in questions)
    _require(
        kinds == _QUESTION_ORDER,
        f"snapshot {snapshot_id} questions must be MC then short then short",
    )
    qids: set[str] = set()
    for q in questions:
        qid = _require_str(q["qid"], "each question needs a qid")
        _require(qid not in qids, "question qids must be unique per snapshot")
        qids.add(qid)
        _require_str(q["prompt"], "each question needs a prompt")
        _require_str(q["key"], "each question key must be readable frozen text")
        _require_str(q["evidence"], "each question needs pinned evidence")
        rubric = q.get("rubric") or {}
        if q["kind"] == "multiple_choice":
            options = q.get("options") or []
            _require(2 <= len(options) <= 5, "multiple choice needs 2-5 options")
            _require(q["key"] in options, "multiple choice key must be one of the options")
            _require(
                tuple(rubric.get("multiple_choice", ())) == _MC_ANCHORS,
                "MC rubric anchors must be 0/1",
            )
        else:
            _require(
                isinstance(q.get("required_elements"), list),
                "short questions need required_elements",
            )
            _require(
                tuple(rubric.get("short", ())) == _SHORT_ANCHORS,
                "short rubric anchors must be 0/0.5/1",
            )


def _validate_manifest(
    raw: Mapping[str, Any],
) -> tuple[Protocol, tuple[Pair, ...], dict[str, dict[str, Any]]]:
    _require(
        int(raw.get("schema_version", 0)) == SCHEMA_VERSION, "manifest schema_version must be 2"
    )
    _require(int(raw["seed"]) >= 0, "seed must be a non-negative int")
    _require(
        raw.get("product_treatment_id") == PRODUCT_TREATMENT_ID,
        "product_treatment_id must be github+prc",
    )
    _require(
        raw.get("baseline_treatment_id") == BASELINE_TREATMENT_ID,
        "baseline_treatment_id must be github+lens-ci",
    )
    _require(
        raw.get("packet_policy") == PACKET_POLICY, "packet_policy must be use_assigned_tool_only"
    )
    versions = raw.get("evaluator_versions") or {}
    _require(
        all(
            _require_str(versions.get(role, ""), f"evaluator_versions.{role} must be recorded")
            for role in ("evaluator", "adjudicator", "scorer")
        ),
        "evaluator versions must be recorded",
    )
    familiar = list(raw.get("familiar_pr_ids") or [])
    _require(isinstance(familiar, list), "familiar_pr_ids must be a list")

    pairs_raw = raw["pairs"]
    _require(isinstance(pairs_raw, list) and len(pairs_raw) > 0, "manifest needs at least one pair")
    protocol = _build_protocol(raw["protocol"], len(pairs_raw))

    pairs: list[Pair] = []
    snapshots: dict[str, dict[str, Any]] = {}
    identities: set[str] = set()
    forbidden = EXPOSED_PR_IDS | set(str(fid) for fid in familiar)
    seen_pair_ids: set[int] = set()

    for pair_raw in pairs_raw:
        pair_id = int(pair_raw["pair_id"])
        _require(pair_id not in seen_pair_ids, "pair_ids must be unique")
        seen_pair_ids.add(pair_id)
        _require_str(pair_raw.get("matching_rationale", ""), "each pair needs a matching rationale")
        snaps = pair_raw["snapshots"]
        _require(len(snaps) == 2, "each pair has exactly two snapshots")
        _require(
            snaps[0]["change_kind"] == snaps[1]["change_kind"],
            "pair members must share change_kind",
        )

        pair_snaps: list[str] = []
        for snap in snaps:
            sid = _require_str(snap["snapshot_id"], "snapshot_id must be recorded")
            _require(bool(_SNAPSHOT_ID.fullmatch(sid)), "snapshot_id must be a safe opaque name")
            _require(sid not in snapshots, f"duplicate snapshot_id {sid}")
            identity = _require_str(snap["pr_identity"], "pr_identity must be recorded")
            _require(bool(_PR_IDENTITY.match(identity)), "pr_identity must be owner/repo#N")
            _require(
                identity not in identities,
                f"duplicate pr identity {identity} even at a different head",
            )
            identities.add(identity)
            _require(
                identity not in forbidden,
                f"exposed or familiar PR {identity} cannot enter the roster",
            )
            base = _require_sha40(snap["base_sha"], "base_sha must be 40-hex")
            head = _require_sha40(snap["head_sha"], "head_sha must be 40-hex")
            _require(head != base, "head_sha must differ from base_sha")
            _require(
                int(snap["changed_lines"]) <= _MAX_CHANGED_LINES, "changed_lines must be <= 500"
            )
            _require(
                int(snap["changed_files"]) <= _MAX_CHANGED_FILES, "changed_files must be <= 10"
            )
            _require_str(snap["title"], "snapshot title must be recorded")
            generation = snap["generation_seconds"]
            for tool in ("lens", "prc"):
                value = generation[tool]
                if value is None:
                    _require_str(
                        (snap.get("generation_notes") or {}).get(tool),
                        "unmeasured generation time needs a reason",
                    )
                else:
                    _require(
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                        and value > 0,
                        "generation_seconds must record positive finite measured times or explicit unknowns",
                    )
            contamination = snap["contamination"]
            _require(
                isinstance(contamination["lens_present_in_github"], bool),
                "lens_present_in_github must be a bool",
            )
            _require(isinstance(contamination.get("other_bots"), list), "other_bots must be a list")
            _require_str(
                contamination.get("comparative_status", ""), "comparative_status must be recorded"
            )
            arts = snap["artifacts"]
            _require(
                all(
                    _require_str(arts.get(tool, ""), f"artifacts.{tool} must be recorded")
                    for tool in ("github", "lens", "prc")
                ),
                "all three artifact trees must be recorded",
            )
            _validate_questions(snap["questions"], sid)
            _require(
                bool(_SHA64.match(str(snap["prc"]["output_hash"]))),
                "prc output_hash must be 64 hex",
            )

            snapshots[sid] = snap
            pair_snaps.append(sid)

        pairs.append(Pair(pair_id=pair_id, snapshot_ids=(pair_snaps[0], pair_snaps[1])))

    return protocol, tuple(pairs), snapshots


@dataclass(frozen=True)
class LoadedManifest:
    root: Path
    protocol: Protocol
    pairs: tuple[Pair, ...]
    snapshots: Mapping[str, Mapping[str, Any]]
    seed: int


def load_manifest(manifest_path: Path) -> LoadedManifest:
    root = manifest_path.resolve().parent
    raw = json.loads(manifest_path.read_text())
    protocol, pairs, snapshots = _validate_manifest(raw)
    for snap in snapshots.values():
        for tool in ("github", "lens", "prc"):
            directory = _artifact_path(root, snap["artifacts"][tool])
            _require(
                not any(path.is_symlink() for path in directory.rglob("*")),
                "artifact tree contains a symlink",
            )

    return LoadedManifest(
        root=root, protocol=protocol, pairs=pairs, snapshots=snapshots, seed=int(raw["seed"])
    )


def _artifact_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    _require(not path.is_absolute() and ".." not in path.parts, "artifact path escapes its root")
    candidate = root / path
    _require(candidate.resolve().is_relative_to(root.resolve()), "artifact path escapes its root")
    _require(
        not any(
            part.is_symlink()
            for part in (candidate, *candidate.parents)
            if part != root and part.is_relative_to(root)
        ),
        "artifact path contains a symlink",
    )
    return candidate


def tree_hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _drift_checks(manifest: LoadedManifest, study_dir: Path) -> None:
    for sid, snap in manifest.snapshots.items():
        for tool in ("github", "lens", "prc"):
            source_dir = manifest.root / snap["artifacts"][tool]
            _require(source_dir.is_dir(), f"missing {tool} artifact tree for {sid}")
        _validate_lens_record(snap, manifest.root / snap["artifacts"]["lens"])
        _validate_prc_record(snap, manifest.root / snap["artifacts"]["prc"])
        study_tree = study_dir / "snapshots" / sid
        _require(study_tree.is_dir(), f"study is missing copied tree for {sid}")


def _identity_patterns(snap: Mapping[str, Any]) -> list[re.Pattern[bytes]]:
    owner_repo, number = str(snap["pr_identity"]).split("#")
    repo = re.escape(owner_repo.encode())

    return [
        re.compile(rb"(?<![A-Za-z0-9_.-])" + repo + rb"#" + number.encode() + rb"(?![0-9])"),
        re.compile(repo + rb"/pull/" + number.encode() + rb"(?![0-9])"),
        re.compile(str(snap["head_sha"]).encode()),
    ]


def _reject_cross_reading_leaks(manifest: LoadedManifest) -> None:
    """Refuse any artifact file that names a different reading's PR or head."""

    patterns = {sid: _identity_patterns(snap) for sid, snap in manifest.snapshots.items()}
    for sid, snap in manifest.snapshots.items():
        others = [pattern for other, found in patterns.items() if other != sid for pattern in found]
        for tool in ("github", "lens", "prc"):
            tree = manifest.root / snap["artifacts"][tool]
            for path in sorted(tree.rglob("*")):
                if not path.is_file():
                    continue
                data = path.read_bytes()
                _require(
                    not any(pattern.search(data) for pattern in others),
                    f"{tool} artifact {path.relative_to(tree)} for {sid} names another reading",
                )


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def prepare_study(manifest_path: Path, out: Path) -> dict[str, Any]:
    """Validate, seal, assign, copy artifact trees, and write the study files."""

    out = out.resolve()
    _require(not out.exists(), f"study directory {out} already exists")
    manifest = load_manifest(manifest_path)

    roster: list[str] = []
    instrument_ids: dict[str, str] = {}
    for sid, snap in manifest.snapshots.items():
        roster.append(sid)
        instrument_ids[sid] = hashlib.sha256(
            json.dumps(snap["questions"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    sealed = seal_experiment(
        roster=roster,
        pairing=manifest.pairs,
        instrument_ids=instrument_ids,
        product_treatment_id=PRODUCT_TREATMENT_ID,
        baseline_treatment_id=BASELINE_TREATMENT_ID,
        evaluator_versions={"evaluator": "", "adjudicator": "", "scorer": ""},
        protocol=manifest.protocol,
    )
    raw_manifest: dict[str, Any] = json.loads(manifest_path.read_text())
    payload: dict[str, Any] = dict(sealed.payload)
    payload["evaluator_versions"] = dict(raw_manifest["evaluator_versions"])
    payload["packet_policy"] = PACKET_POLICY
    payload["familiar_pr_ids"] = list(str(fid) for fid in raw_manifest["familiar_pr_ids"])
    payload["seed"] = manifest.seed
    payload["study_mode"] = raw_manifest.get("study_mode", "real")
    _require(payload["study_mode"] in ("real", "fixture"), "study_mode must be real or fixture")
    sealed = SealedExperiment(payload=payload, digest=seal_digest(payload))

    assignment = assign(manifest.pairs, manifest.seed, manifest.protocol)

    snapshot_meta: dict[str, dict[str, Any]] = {}
    for snap in manifest.snapshots.values():
        _validate_lens_record(snap, manifest.root / snap["artifacts"]["lens"])
        _validate_prc_record(snap, manifest.root / snap["artifacts"]["prc"])
    _reject_cross_reading_leaks(manifest)
    out.mkdir(parents=True)
    try:
        for sid, snap in manifest.snapshots.items():
            meta = {
                "pr_identity": snap["pr_identity"],
                "base_sha": snap["base_sha"],
                "head_sha": snap["head_sha"],
                "title": snap["title"],
                "change_kind": snap["change_kind"],
                "generation_seconds": snap["generation_seconds"],
                "generation_notes": snap.get("generation_notes", {}),
                "contamination": snap["contamination"],
                "lens": snap["lens"],
                "lens_body_sha256": hashlib.sha256(
                    _load_comment_body(
                        manifest.root / snap["artifacts"]["lens"], snap["lens"]["comment_path"]
                    ).encode()
                ).hexdigest(),
                "trees": {},
            }
            for tool in ("github", "lens", "prc"):
                source_dir = manifest.root / snap["artifacts"][tool]
                shutil.copytree(source_dir, out / "snapshots" / sid / tool)
                meta["trees"][tool] = tree_hashes(out / "snapshots" / sid / tool)
            snapshot_meta[sid] = meta

        study = {
            "schema_version": SCHEMA_VERSION,
            "sealed": {"payload": sealed.payload, "digest": sealed.digest},
            "protocol": sealed.payload["protocol"],
            "seed": manifest.seed,
            "questions": {sid: snap["questions"] for sid, snap in manifest.snapshots.items()},
            "assignment": {
                "seed": assignment.seed,
                "pair_order": list(assignment.pair_order),
                "assignment_draws": list(assignment.assignment_draws),
                "exposure_draws": list(assignment.exposure_draws),
                "card_permutation": list(assignment.card_permutation),
                "pairs": [
                    {
                        "pair_id": pair.pair_id,
                        "product_snapshot_id": pair.product_snapshot_id,
                        "baseline_snapshot_id": pair.baseline_snapshot_id,
                        "product_first": pair.product_first,
                    }
                    for pair in assignment.pairs
                ],
            },
            "snapshots": snapshot_meta,
        }
        trials: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        product_of_pair = {
            pair["pair_id"]: pair["product_snapshot_id"] for pair in study["assignment"]["pairs"]
        }
        for pair_id in study["assignment"]["pair_order"]:
            pair_meta = next(
                pair for pair in study["assignment"]["pairs"] if pair["pair_id"] == pair_id
            )
            product_first = pair_meta["product_first"]
            pair_snaps = [pair_meta["product_snapshot_id"], pair_meta["baseline_snapshot_id"]]
            if not product_first:
                pair_snaps.reverse()
            for sid in pair_snaps:
                condition = "product" if product_of_pair[pair_id] == sid else "baseline"
                trial_id = secrets.token_hex(8)
                trials[trial_id] = {
                    "trial_id": trial_id,
                    "pair_id": pair_id,
                    "snapshot_id": sid,
                    "condition": condition,
                    "state": "pending",
                    "started_at": None,
                    "ended_at": None,
                    "answers": {},
                    "confidence": {},
                    "familiarity": None,
                    "cross_exposure_start": None,
                    "cross_exposure_submit": None,
                }
                order.append(trial_id)

        payload["study_data"] = {
            "questions": study["questions"],
            "snapshots": study["snapshots"],
            "assignment": study["assignment"],
            "order": order,
            "trials": {
                tid: {key: trial[key] for key in ("pair_id", "snapshot_id", "condition")}
                for tid, trial in trials.items()
            },
            "matching_rationales": {
                str(pair["pair_id"]): pair["matching_rationale"] for pair in raw_manifest["pairs"]
            },
        }
        sealed = SealedExperiment(payload=payload, digest=seal_digest(payload))
        study["sealed"] = sealed.to_json_dict()
        _atomic_write_json(out / "study.json", study)
        session_state = {
            "schema_version": SCHEMA_VERSION,
            "study_digest": sealed.digest,
            "closed": False,
            "order": order,
            "trials": trials,
            "active_trial": None,
        }
        _atomic_write_json(out / "session.json", session_state)
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise

    return {"study_dir": str(out), "digest": sealed.digest, "trials": len(trials)}


@dataclass(frozen=True)
class StudyTrial:
    trial_id: str
    pair_id: int
    snapshot_id: str
    condition: str
    state: str


@dataclass(frozen=True)
class Study:
    root: Path
    sealed: SealedExperiment
    protocol: Protocol
    trials: Mapping[str, StudyTrial]
    session: dict[str, Any]
    study: dict[str, Any]


def study_digest(study_dir: Path) -> str:
    data = json.loads((study_dir / "study.json").read_text())

    return str(data["sealed"]["digest"])


def verify_digest(sealed: SealedExperiment) -> bool:
    return verify_seal(sealed)


def load_study(study_dir: Path) -> Study:
    study_dir = study_dir.resolve()
    raw = json.loads((study_dir / "study.json").read_text())
    sealed = SealedExperiment(payload=raw["sealed"]["payload"], digest=raw["sealed"]["digest"])
    _require(verify_seal(sealed), "study seal drift: payload no longer hashes to the digest")
    protocol = Protocol(**sealed.payload["protocol"])
    session_state = json.loads((study_dir / "session.json").read_text())
    _require(session_state["study_digest"] == sealed.digest, "session digest drift")
    frozen = sealed.payload["study_data"]
    for field in ("questions", "snapshots", "assignment"):
        _require(raw[field] == frozen[field], f"study {field} drift")
    _require(session_state["order"] == frozen["order"], "session assignment order drift")
    actual = {
        tid: {key: trial[key] for key in ("pair_id", "snapshot_id", "condition")}
        for tid, trial in session_state["trials"].items()
    }
    _require(actual == frozen["trials"], "session assignment drift")

    for sid, meta in raw["snapshots"].items():
        for tool in ("github", "lens", "prc"):
            current = tree_hashes(study_dir / "snapshots" / sid / tool)
            _require(current == meta["trees"][tool], f"artifact drift in {sid}/{tool}")

    trials = {
        trial_id: StudyTrial(
            trial_id=trial_id,
            pair_id=int(entry["pair_id"]),
            snapshot_id=str(entry["snapshot_id"]),
            condition=str(entry["condition"]),
            state=str(entry["state"]),
        )
        for trial_id, entry in session_state["trials"].items()
    }

    study = Study(
        root=study_dir,
        sealed=sealed,
        protocol=protocol,
        trials=trials,
        session=session_state,
        study=raw,
    )

    return study


def close_study(study_dir: Path) -> None:
    session_state = json.loads((study_dir / "session.json").read_text())
    _require(not session_state.get("closed"), "study is already closed")
    active = session_state.get("active_trial")
    _require(active is None, "close refuses while a trial is active; submit or abort it first")
    session_state["closed"] = True
    _atomic_write_json(study_dir / "session.json", session_state)


def _questions_for(study_dir: Path, snapshot_id: str) -> list[dict[str, Any]]:
    raw = json.loads((study_dir / "study.json").read_text())
    manifest_questions = raw.get("questions") or {}
    _require(snapshot_id in manifest_questions, f"study questions are missing for {snapshot_id}")

    return list(manifest_questions[snapshot_id])


def _blinded_items(study_dir: Path, session_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for trial_id, entry in session_state["trials"].items():
        if entry["state"] == "pending":
            continue
        questions = _questions_for(study_dir, str(entry["snapshot_id"]))
        for question in questions:
            qid = question["qid"]
            items.append(
                {
                    "trial_id": trial_id,
                    "qid": qid,
                    "kind": question["kind"],
                    "prompt": question["prompt"],
                    "options": question.get("options"),
                    "answer": entry["answers"].get(qid),
                    "confidence": entry["confidence"].get(qid),
                    "key": question["key"],
                    "required_elements": question.get("required_elements"),
                    "rubric": question["rubric"],
                    "rubric_anchors": question.get("rubric_anchors", {}),
                }
            )

    return items


def export_blinded(study_dir: Path, out_path: Path) -> dict[str, Any]:
    load_study(study_dir)
    session_state = json.loads((study_dir / "session.json").read_text())
    _require(session_state.get("closed") is True, "export requires a closed study")
    digest = study_digest(study_dir)
    document = {
        "schema_version": SCHEMA_VERSION,
        "study_digest": digest,
        "blinding_label": "condition-blinded; content-derived identity inference not excluded",
        "rubric_evidence_caveat": (
            "Keys and required elements are included because the study is closed; "
            "score only against these anchors. Prompts and answers may reveal PR content; "
            "the blinding covers the condition and assignment, not identity inference. "
            "Evidence references are withheld from this sheet."
        ),
        "items": _blinded_items(study_dir, session_state),
    }
    _atomic_write_json(out_path, document)

    return document


_VALID_ANCHORS: dict[str, tuple[float, ...]] = {
    "multiple_choice": _MC_ANCHORS,
    "short": _SHORT_ANCHORS,
}


def apply_scores(study_dir: Path, scores_path: Path, out_path: Path) -> dict[str, Any]:
    study = load_study(study_dir)
    session_state = json.loads((study_dir / "session.json").read_text())
    _require(session_state.get("closed") is True, "grading requires a closed study")
    scores_raw = json.loads(scores_path.read_text())
    _require(scores_raw.get("study_digest") == study.sealed.digest, "scores study_digest drift")
    scores = scores_raw["scores"]

    scored_trials = {
        trial_id: entry
        for trial_id, entry in session_state["trials"].items()
        if entry["state"] in ("submitted", "aborted", "timed_out")
    }
    _require(set(scores) == set(scored_trials), "scores must cover exactly the terminal trials")

    for trial_id, entry in scored_trials.items():
        questions = _questions_for(study_dir, str(entry["snapshot_id"]))
        qids = [str(q["qid"]) for q in questions]
        awarded = scores[trial_id]
        _require(set(awarded) == set(qids), f"trial {trial_id} must be scored on exactly its qids")
        for question in questions:
            qid = str(question["qid"])
            value = awarded[qid]
            _require(
                isinstance(value, (int, float)) and not isinstance(value, bool),
                "scores must be numbers",
            )
            anchors = _VALID_ANCHORS[str(question["kind"])]
            _require(
                float(value) in anchors, f"score {value} is off the {question['kind']} anchors"
            )
            if entry["answers"].get(qid) in (None, ""):
                _require(float(value) == 0.0, "blank answers cannot be awarded")
            if question["kind"] == "multiple_choice":
                expected = float(entry["answers"].get(qid) == question["key"])
                _require(
                    float(value) == expected, "multiple-choice score does not match the frozen key"
                )

    by_snapshot = {trial.snapshot_id: trial for trial in study.trials.values()}
    condition_of = {sid: trial.condition for sid, trial in by_snapshot.items()}
    trial_of_snapshot = {
        entry["snapshot_id"]: (trial_id, entry)
        for trial_id, entry in session_state["trials"].items()
    }

    pairs_out: list[dict[str, Any]] = []
    for pair in study.sealed.payload["pairing"]:
        sides: dict[str, dict[str, Any]] = {}
        for sid in pair["snapshot_ids"]:
            trial_id, entry = trial_of_snapshot[sid]
            condition = condition_of[sid]
            questions = _questions_for(study_dir, sid)
            if entry["state"] == "pending":
                result: dict[str, Any] = {"snapshot_id": sid, "state": "unknown"}
            else:
                awarded = [scores[trial_id].get(str(q["qid"])) for q in questions]
                item_scores = [float(v) for v in awarded]
                elapsed = None
                if entry.get("started_at") and entry.get("ended_at"):
                    elapsed = min(
                        float(entry["ended_at"]) - float(entry["started_at"]),
                        study.protocol.deadline_seconds,
                    )
                result = {
                    "snapshot_id": sid,
                    "state": "scored",
                    "item_scores": item_scores,
                    "aborted": entry["state"] == "aborted",
                    "confidences": [entry["confidence"].get(str(q["qid"])) for q in questions],
                    "elapsed_seconds": elapsed,
                    "censored": elapsed is not None and elapsed >= study.protocol.deadline_seconds,
                }
            sides[condition] = result
        pairs_out.append(
            {
                "pair_id": int(pair["pair_id"]),
                "product": sides["product"],
                "baseline": sides["baseline"],
            }
        )

    document = {
        "schema_version": SCHEMA_VERSION,
        "study_digest": study.sealed.digest,
        "protocol": study.sealed.payload["protocol"],
        "interpretation": "exploratory pilot; not evidence of release readiness",
        "deviations": [
            {
                "trial_id": tid,
                "snapshot_id": entry["snapshot_id"],
                "state": entry["state"],
                "ineligible": entry.get("ineligible"),
                "familiarity": entry.get("familiarity"),
                "cross_exposure_start": entry.get("cross_exposure_start"),
                "cross_exposure_submit": entry.get("cross_exposure_submit"),
                "contamination": study.sealed.payload["study_data"]["snapshots"][
                    entry["snapshot_id"]
                ]["contamination"],
            }
            for tid, entry in session_state["trials"].items()
        ],
        "pairs": pairs_out,
    }
    _atomic_write_json(out_path, document)

    return document

"""Fixture builder for paired-eval tests: a valid manifest plus artifact trees."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha1_hex(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


STICKY_MARKER = "<!-- pr-lens:sticky -->"
STATE_MARKER = "<!-- pr-lens:state "


class PairedFixture:
    def __init__(self, root: Path, data: dict[str, Any]) -> None:
        self.root = root
        self.data = data

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def study(self) -> Path:
        return self.root / "study"

    def save(self) -> Path:
        self.manifest.write_text(json.dumps(self.data, indent=2))

        return self.manifest


def _artifact_trees(root: Path, data: dict[str, Any]) -> None:
    for entry in data["pairs"]:
        for snap in entry["snapshots"]:
            sid = snap["snapshot_id"]
            base = root / snap["artifacts"]["github"]
            base.mkdir(parents=True, exist_ok=True)
            (base / "index.html").write_text(f"<h1>{snap['title']}</h1><p>Files changed</p>")

            lens = root / snap["artifacts"]["lens"]
            lens.mkdir(parents=True, exist_ok=True)
            head = snap["head_sha"]
            body = (
                f"{STICKY_MARKER} architecture diagram\n"
                f'{STATE_MARKER}{{"headSha": "{head}", "state": "published"}} -->\n'
                "Changed parts amber, new parts green."
            )
            (lens / "comment.json").write_text(
                json.dumps(
                    {
                        "id": snap["lens"]["comment_id"],
                        "user": {"login": snap["lens"]["comment_author"]},
                        "body": body,
                    }
                )
            )
            svg_bytes = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
            svg_name = hashlib.sha256(svg_bytes.encode()).hexdigest()[:32] + ".svg"
            (lens / svg_name).write_text(svg_bytes)
            (lens / "index.html").write_text(
                "<h1>Frozen Lens CI fixture</h1><p>Demonstration material only.</p>"
            )
            snap["lens"]["page_sha256"] = hashlib.sha256(
                (lens / "index.html").read_bytes()
            ).hexdigest()
            snap["lens"]["svg_files"] = [
                {"path": svg_name, "sha256": hashlib.sha256(svg_bytes.encode()).hexdigest()}
            ]

            (lens / "check_run.json").write_text(
                json.dumps(
                    {
                        "id": snap["lens"]["check_run_id"],
                        "head_sha": head,
                        "status": "completed",
                        "conclusion": "success",
                        "app": {"slug": snap["lens"]["check_app_slug"]},
                    }
                )
            )

            prc_dir = root / snap["artifacts"]["prc"]
            prc_dir.mkdir(parents=True, exist_ok=True)
            prc_index = f"<div>PRC review output for {sid}</div>"
            (prc_dir / "index.html").write_text(prc_index)
            (prc_dir / "map.json").write_text(
                json.dumps({"base_sha": snap["base_sha"], "head_sha": snap["head_sha"]})
            )
            snap["prc"]["output_hash"] = hashlib.sha256(prc_index.encode()).hexdigest()


def build_manifest(root: Path, pairs: int = 1) -> PairedFixture:
    root.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "schema_version": 2,
        "study_mode": "fixture",
        "seed": 424242,
        "protocol": {
            "pair_count": pairs,
            "pairs_per_session": pairs,
            "session_days": [1],
        },
        "product_treatment_id": "github+prc",
        "baseline_treatment_id": "github+lens-ci",
        "evaluator_versions": {"evaluator": "ev-1", "adjudicator": "adj-1", "scorer": "sc-1"},
        "packet_policy": "use_assigned_tool_only",
        "familiar_pr_ids": ["some-familiar/repo#7"],
        "pairs": [],
    }

    for n in range(1, pairs + 1):
        data["pairs"].append(
            {
                "pair_id": n,
                "matching_rationale": "same subsystem, similar size, both agent-authored",
                "snapshots": [
                    _snapshot(root, f"{n}a", f"vendor-{n}/cache-{n}#{100 + n}"),
                    _snapshot(root, f"{n}b", f"vendor-{n}/cache-{n}#{200 + n}"),
                ],
            }
        )

    fixture = PairedFixture(root, data)
    _artifact_trees(root, data)
    fixture.save()
    return fixture


def _snapshot(root: Path, sid: str, identity: str) -> dict[str, Any]:
    base = sha1_hex(f"base-{sid}")
    head = sha1_hex(f"head-{sid}")
    return {
        "snapshot_id": sid,
        "pr_identity": identity,
        "base_sha": base,
        "head_sha": head,
        "title": f"Fix eviction for {sid}",
        "changed_lines": 120,
        "changed_files": 3,
        "change_kind": "refactor-cache",
        "generation_seconds": {"lens": 12.5, "prc": 18.0},
        "contamination": {
            "lens_present_in_github": True,
            "other_bots": ["renovate[bot]"],
            "comparative_status": "same-repo-adjacent",
        },
        "artifacts": {
            "github": f"artifacts/{sid}/github",
            "lens": f"artifacts/{sid}/lens",
            "prc": f"artifacts/{sid}/prc",
        },
        "lens": {
            "comment_id": 1000 + len(sid),
            "comment_url": f"https://github.com/{identity.split('#')[0]}/pull/{identity.split('#')[1]}#issuecomment-{1000 + len(sid)}",
            "comment_path": "comment.json",
            "comment_author": "coldtea-pr-lens[bot]",
            "reviewed_sha": head,
            "headSha": head,
            "graphKey": f"prlens:graph:{head}",
            "check_run_id": 77,
            "check_app_slug": "coldtea-pr-lens",
            "check_head_sha": head,
            "version": "hosted-app captured 2026-10-11T12:00:00Z",
            "svg_files": [],
        },
        "prc": {
            "base_sha": base,
            "head_sha": head,
            "output_hash": "placeholder",
            "render_identity": "prc-map-1",
            "index_path": "index.html",
        },
        "questions": [
            {
                "qid": "q1",
                "kind": "multiple_choice",
                "prompt": "Which file owns the eviction policy?",
                "options": ["cache/evict.go", "cache/store.go", "docs/notes.md"],
                "key": "cache/evict.go",
                "required_elements": [],
                "rubric": {"multiple_choice": [0.0, 1.0], "short": [0.0, 0.5, 1.0]},
                "evidence": "github tree, cache/evict.go diff hunk",
            },
            {
                "qid": "q2",
                "kind": "short",
                "prompt": "Explain the eviction trigger in two sentences.",
                "key": "trigger named with evidence",
                "required_elements": ["trigger", "evidence line"],
                "rubric": {"multiple_choice": [0.0, 1.0], "short": [0.0, 0.5, 1.0]},
                "evidence": "github tree, cache/evict.go",
            },
            {
                "qid": "q3",
                "kind": "short",
                "prompt": "What breaks if the TTL is zero?",
                "key": "loop or churn behavior",
                "required_elements": ["zero TTL effect"],
                "rubric": {"multiple_choice": [0.0, 1.0], "short": [0.0, 0.5, 1.0]},
                "evidence": "github tree, cache/store.go",
            },
        ],
    }

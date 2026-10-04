"""`prc` entry point. Thin: parse arguments, call the pipeline, print identities."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import time
from pathlib import Path

from prc.controller import fixture_suite
from prc.fixture_source import FIXTURE_EPOCH
from prc.github_source import GitHubSource
from prc.identity import to_jsonable
from prc.model import PrRef
from prc.pipeline import run_brief, run_decide, run_map, run_review, run_status
from prc.scenarios import SCENARIOS, add_mutation, load_fixture
from prc.source import PullRequestSource
from prc.store import StaleExpectation, Store
from prc.verification import EligibilityPolicy

_GITHUB = re.compile(r"^github:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#(\d+)$")
_PR_URL = re.compile(
    r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)(?:[/?#].*)?$"
)


class FixtureClock:
    """Deterministic clock: fixture runs reproduce byte-identical artifacts."""

    def __init__(self, offset: float = 0.0) -> None:
        self.now = FIXTURE_EPOCH + offset

    def __call__(self) -> float:
        self.now += 1.0

        return self.now


def _resolve(spec: str, store_dir: Path) -> tuple[PullRequestSource, PrRef]:
    if spec.startswith("fixture:"):
        name = spec.split(":", 1)[1]

        if name not in SCENARIOS:
            raise SystemExit(f"unknown fixture {name!r}; choose from {sorted(SCENARIOS)}")

        source, ref = load_fixture(name, store_dir / "fixtures")

        return source, ref

    match = _GITHUB.match(spec) or _PR_URL.match(spec)

    if match is None:
        raise SystemExit(
            "source must be fixture:<name>, github:<owner>/<repo>#<number> "
            "or https://github.com/<owner>/<repo>/pull/<number>"
        )

    return GitHubSource(store_dir / "git-cache"), PrRef(match[1], match[2], int(match[3]))


def _clock(spec: str, offset: float):  # type: ignore[no-untyped-def]
    return FixtureClock(offset) if spec.startswith("fixture:") else time.time


def _report_json(report: object) -> object:
    return to_jsonable(dataclasses.asdict(report))  # type: ignore[call-overload]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prc", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("review", "status", "decide", "brief", "map"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--source", required=True)
        cmd.add_argument("--store", type=Path, default=Path("artifacts/store"))
        cmd.add_argument("--clock-offset", type=float, default=0.0, help="fixture clock only")
        cmd.add_argument(
            "--required-check",
            action="append",
            help="check name the policy requires (repeatable); fixtures default to unit-tests, merged-ci",
        )

        if name == "review":
            cmd.add_argument("--out", type=Path, default=Path("artifacts/reviews"))

        if name == "brief":
            cmd.add_argument("--out", type=Path, default=Path("artifacts/briefs"))

        if name == "map":
            cmd.add_argument("--out", type=Path, default=Path("artifacts/maps"))

        if name == "decide":
            cmd.add_argument("--expect-snapshot", required=True)
            cmd.add_argument("--expect-view", required=True)
            cmd.add_argument("--reviewer", required=True)
            cmd.add_argument(
                "--decision", required=True, choices=["approve", "reject", "request_changes"]
            )
            cmd.add_argument("--confidence", type=int)
            cmd.add_argument("--note", default="")

    mutate = sub.add_parser("fixture-mutate", help="simulate a provider change on a fixture")
    mutate.add_argument("name")
    mutate.add_argument("mutation", choices=["edit-title", "rerun-check", "expire-checks"])
    mutate.add_argument("--store", type=Path, default=Path("artifacts/store"))

    analyze = sub.add_parser("eval-analyze", help="analyze recorded pilot pair outcomes")
    analyze.add_argument("results", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy = EligibilityPolicy()

    if args.command == "fixture-mutate":
        print(json.dumps(add_mutation(args.name, args.store / "fixtures", args.mutation)))

        return 0

    if args.command == "eval-analyze":
        from prc.evaluation.analysis import analyze
        from prc.evaluation.io import load_pairs

        print(json.dumps(_report_json(analyze(load_pairs(args.results))), indent=2, default=str))

        return 0

    if args.required_check is not None:
        policy = EligibilityPolicy(required_names=tuple(args.required_check))
    elif not args.source.startswith("fixture:"):
        policy = EligibilityPolicy(required_names=())

    source, ref = _resolve(args.source, args.store)

    if args.command == "brief":
        brief = run_brief(source, ref, _clock(args.source, args.clock_offset), policy, args.out)
        print(
            json.dumps(
                {
                    "source": source.label,
                    "live_verified": source.live_verified,
                    "snapshot_id": brief.snapshot_id,
                    "brief": str(brief.path),
                    "mismatches": len(brief.brief.mismatches),
                    "look_first": [pointer.path for pointer in brief.brief.look_first],
                },
                indent=2,
            )
        )

        return 0

    if args.command == "map":
        mapped = run_map(source, ref, _clock(args.source, args.clock_offset), policy, args.out)
        print(
            json.dumps(
                {
                    "source": source.label,
                    "live_verified": source.live_verified,
                    "snapshot_id": mapped.snapshot_id,
                    "html": str(mapped.html),
                    "json": str(mapped.json),
                    "symbols": sum(s.status != "context" for s in mapped.map.symbols),
                    "edges": len(mapped.map.edges),
                    "steps": len(mapped.map.tour),
                },
                indent=2,
            )
        )

        return 0

    store = Store(args.store / "prc.sqlite")
    clock = _clock(args.source, args.clock_offset)

    if args.command == "review":
        result = run_review(source, ref, store, fixture_suite(), clock, policy, args.out)
        print(
            json.dumps(
                {
                    "source": source.label,
                    "live_verified": source.live_verified,
                    "snapshot_id": result.snapshot_id,
                    "semantic_id": result.semantic_id,
                    "view_id": result.view_id,
                    "capture_consistency": result.consistency,
                    "coverage_gaps": result.gap_count,
                    "canonical_publication_won": result.won_canonicalization,
                    "out_dir": str(result.out_dir),
                    "files": list(result.files),
                },
                indent=2,
            )
        )

        return 0

    if args.command == "status":
        snapshot_id, view_id, report = run_status(source, ref, store, policy, clock)
        now = clock()
        print(
            json.dumps(
                {
                    "snapshot_id": snapshot_id,
                    "view_id": view_id,
                    "status": report.status,
                    "effective_now": report.effective(now),
                    "last_observed_at": report.observed_finished_at,
                    "freshness_deadline": report.deadline,
                    "differences": list(report.differences),
                    "detail": report.detail,
                    "note": "observational; not an atomic provider state or merge authorization",
                },
                indent=2,
            )
        )

        return 0

    try:
        decision_id, report = run_decide(
            source, ref, store, policy, clock,
            expected_snapshot_id=args.expect_snapshot,
            expected_view_id=args.expect_view,
            reviewer=args.reviewer,
            decision=args.decision,
            confidence=args.confidence,
            note=args.note,
        )  # fmt: skip
    except StaleExpectation as error:
        print(f"refused: {error}", file=sys.stderr)

        return 2

    print(
        json.dumps(
            {"decision_id": decision_id, "freshness": report.status, "recorded": args.decision}
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

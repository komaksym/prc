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
from prc.pipeline import (
    ExplainCheckError,
    run_brief,
    run_decide,
    run_explain,
    run_map,
    run_review,
    run_status,
)
from prc.presentation import map_video
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
            cmd.add_argument(
                "--video", action="store_true", help="also write tour.mp4 and card.png"
            )

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

    explain = sub.add_parser("explain", help="render a narrated explainer video for a PR")
    explain.add_argument("--source", required=True)
    explain.add_argument("--store", type=Path, default=Path("artifacts/store"))
    explain.add_argument("--clock-offset", type=float, default=0.0, help="fixture clock only")
    explain.add_argument("--map", type=Path, default=None, help="stored map.json to render from")
    explain.add_argument("--board", type=Path, default=None, help="checked board.json to render")
    explain.add_argument("--out", type=Path, default=Path("artifacts/explain"))
    explain.add_argument(
        "--voice",
        default="auto",
        choices=["auto", "kokoro", "say", "none"],
        help="narration backend; auto is the first one that works",
    )

    board = sub.add_parser("board", help="board tools for the story a video tells")
    board_sub = board.add_subparsers(dest="board_command", required=True)
    board_sub.add_parser("guide", help="print the board-writing guide")
    board_cmds = {}
    for name in ("show", "find", "coverage", "check"):
        cmd = board_sub.add_parser(name)
        cmd.add_argument("--source", default=None)
        cmd.add_argument("--map", type=Path, default=None)
        cmd.add_argument("--store", type=Path, default=Path("artifacts/store"))
        cmd.add_argument("--clock-offset", type=float, default=0.0, help="fixture clock only")
        board_cmds[name] = cmd

    board_cmds["show"].add_argument(
        "paths", nargs="*", help="only files with one of these in the path"
    )
    board_cmds["find"].add_argument("needles", nargs="+")
    board_cmds["find"].add_argument("--path", default=None, help="only files with this in the path")
    board_cmds["coverage"].add_argument("board", type=Path)
    board_cmds["check"].add_argument("board", type=Path)

    skill = sub.add_parser("skill", help="install the board-writer skill for your agent")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    install = skill_sub.add_parser("install", help="install the prc-explain skill")
    install.add_argument("agent", choices=["claude", "codex"])
    install.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="folder to install into (default ~/.claude/skills for claude, "
        "the current folder's AGENTS.md for codex; asks before touching it)",
    )

    sub.add_parser("doctor", help="check the tools explain needs")

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

    required = getattr(args, "required_check", None)
    has_source = getattr(args, "source", None)

    if required is not None:
        policy = EligibilityPolicy(required_names=tuple(required))
    elif has_source is not None and not has_source.startswith("fixture:"):
        policy = EligibilityPolicy(required_names=())
    else:
        policy = EligibilityPolicy()

    resolved: tuple[PullRequestSource, PrRef] | None = (
        _resolve(has_source, args.store)
        if args.command in ("review", "status", "decide", "brief", "map") and has_source
        else None
    )

    if resolved is not None:
        source, ref = resolved

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
        video = None

        try:
            if args.video:
                map_video.check_tools()

            mapped = run_map(source, ref, _clock(args.source, args.clock_offset), policy, args.out)

            if args.video:
                video = map_video.make_video(mapped.html, mapped.html.parent)
        except map_video.VideoError as error:
            raise SystemExit(f"prc map --video: {error}") from error

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
                    **(
                        {
                            "mp4": str(video.mp4),
                            "card": str(video.card),
                            "video_seconds": video.seconds,
                        }
                        if video
                        else {}
                    ),
                },
                indent=2,
            )
        )

        return 0

    if args.command == "explain":
        from prc.explainer.render import RenderError
        from prc.explainer.voice import VoiceError

        source, ref = _resolve(args.source, args.store)

        try:
            explained = run_explain(
                source,
                ref,
                _clock(args.source, args.clock_offset),
                policy,
                args.out,
                board_path=args.board,
                map_path=args.map,
                voice=args.voice,
            )
        except ExplainCheckError as error:
            print(str(error), file=sys.stderr)

            return 2
        except (RenderError, VoiceError) as error:
            raise SystemExit(f"prc explain: {error}") from error

        print(
            json.dumps(
                {
                    "source": source.label,
                    "out": str(explained.out_dir),
                    "map": str(explained.map_json),
                    "board": str(explained.board_json) if explained.board_json else None,
                    "video": str(explained.video) if explained.video else None,
                    "doc": str(explained.doc_html) if explained.doc_html else None,
                    "card": str(explained.card_png) if explained.card_png else None,
                    "comment": str(explained.comment_md),
                    "duration": explained.duration,
                    "estimate": explained.estimate,
                    "check_passed": explained.check_passed,
                },
                indent=2,
            )
        )

        return 0

    if args.command == "board":
        from prc.explainer import boards
        from prc.pipeline import load_map_dict

        if args.board_command == "guide":
            print(boards.guide(), end="")

            return 0

        if args.map is not None:
            used = json.loads(args.map.read_text())
        elif args.source:
            source, ref = _resolve(args.source, args.store)
            used, _, _, _ = load_map_dict(
                source, ref, _clock(args.source, args.clock_offset), policy, None
            )
        else:
            raise SystemExit(f"prc board {args.board_command} needs --source or --map")

        if args.board_command == "show":
            print(boards.show(used, args.paths), end="")

            return 0

        if args.board_command == "find":
            print(boards.find(used, args.needles, args.path), end="")

            return 0

        board_doc = json.loads(args.board.read_text())

        if args.board_command == "coverage":
            print(boards.coverage(board_doc, used), end="")

            return 0

        from prc.explainer.check import verify_board

        try:
            facts = verify_board(board_doc, used)
        except SystemExit as error:
            print(str(error), file=sys.stderr)

            return 2

        print(f"{facts['receipts']} receipts verified")

        return 0

    if args.command == "doctor":
        from prc.explainer import doctor

        print(doctor.report(), end="")

        return 0

    if args.command == "skill":
        from prc import skill as skill_pkg

        if args.skill_command == "install":
            dest = args.dest
            if dest is None:
                dest = skill_pkg.default_dest(args.agent)
                print(
                    f"prc skill install {args.agent} defaults to {dest}. "
                    "That is your own configuration.",
                    file=sys.stderr,
                )
                try:
                    answer = input(f"Install into {dest} anyway? [y/N] ")
                except EOFError:
                    answer = "no"
                if answer.strip().lower() not in ("y", "yes"):
                    print("aborted: nothing written. Re-run with --dest DIR.", file=sys.stderr)

                    return 2
            written = skill_pkg.install(args.agent, dest)
            print(str(written))

            return 0

        raise SystemExit(f"unknown skill command {args.skill_command!r}")

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

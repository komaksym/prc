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
    InfographicMissingError,
    run_brief,
    run_decide,
    run_explain,
    run_review,
    run_status,
)
from prc.presentation import infographic
from prc.scenarios import SCENARIOS, add_mutation, load_fixture
from prc.source import PullRequestSource, SourceError
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

    for name in ("review", "status", "decide", "brief"):
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
    explain.add_argument(
        "--git-dir",
        type=Path,
        default=None,
        help="bare git cache for highlighting when rendering from --map offline",
    )
    explain.add_argument(
        "--voice",
        default="auto",
        choices=["auto", "kokoro", "say", "none"],
        help="narration backend; auto is the first one that works",
    )
    explain.add_argument("--out", type=Path, default=Path("artifacts/explain"))
    explain.add_argument(
        "--infographic",
        type=Path,
        action="append",
        default=[],
        help="candidate infographic PNG to gate (repeatable; first pass wins)",
    )

    board = sub.add_parser("board", help="board tools for the story a video tells")
    board_sub = board.add_subparsers(dest="board_command", required=True)
    board_sub.add_parser("guide", help="print the board-writing guide")
    board_cmds = {}
    for name in ("show", "find", "units", "coverage", "check", "preview"):
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
    board_cmds["preview"].add_argument("board", type=Path)
    board_cmds["preview"].add_argument(
        "--out", type=Path, default=Path("artifacts/preview"), help="stills output folder"
    )
    board_cmds["preview"].add_argument(
        "--git-dir",
        type=Path,
        default=None,
        help="git dir for exact highlight colors (default: from --source, else hunk text)",
    )

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

    hear = sub.add_parser(
        "listen", help="check that a speech recognizer hears every code name in a video"
    )
    hear.add_argument("folder", type=Path, help="an explain output folder")
    hear.add_argument("--engine", default="auto", choices=["auto", "parakeet", "whisper"])

    notes = sub.add_parser("notes-review", help="serve the per-PR notes review hub")
    notes.add_argument("notes_dir", type=Path, help="dir with roster.json and notes.json")
    notes.add_argument("--port", type=int, default=0)

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except SourceError as error:
        print(f"prc: {error}", file=sys.stderr)

        return 1


def _main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy = EligibilityPolicy()

    if args.command == "fixture-mutate":
        print(json.dumps(add_mutation(args.name, args.store / "fixtures", args.mutation)))

        return 0

    if args.command == "notes-review":
        from prc.evaluation.notes import NotesError, serve

        try:
            httpd, url = serve(args.notes_dir, args.port)
        except NotesError as error:
            print(f"prc: {error}", file=sys.stderr)

            return 1
        print(f"notes-review session: {url}", flush=True)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()

        return 0

    if args.command == "listen":
        from prc.explainer.listen import ListenError, listen

        try:
            checked = listen(args.folder, args.engine)
        except ListenError as error:
            print(f"prc: {error}", file=sys.stderr)
            return 2
        if not checked["calibration"]["passed"]:
            print("prc: the recognizer failed its planted controls", file=sys.stderr)
        for token in checked["lost"]:
            print(f"prc: the narration loses {token}", file=sys.stderr)
        summary = {k: checked[k] for k in ("engine", "lost", "passed")}
        print(json.dumps(summary | {"report": str(args.folder / "listening.json")}, indent=2))

        return 0 if checked["passed"] else 1

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
        if args.command in ("review", "status", "decide", "brief") and has_source
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

    if args.command == "explain":
        from prc.explainer.render import RenderError
        from prc.explainer.voice import VoiceError

        source, ref = _resolve(args.source, args.store)
        cands: list[Path] = []
        for cand in args.infographic:
            if not cand.is_file():
                raise SystemExit(f"prc explain: no such --infographic file: {cand}")
            try:
                infographic.read_png(cand)
            except ValueError as error:
                raise SystemExit(f"prc explain: --{error}") from error
            cands.append(cand)

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
                git_dir=str(args.git_dir) if args.git_dir else None,
                infographics=cands,
            )
        except ExplainCheckError as error:
            print(str(error), file=sys.stderr)

            return 2
        except InfographicMissingError as error:
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
                    "page": str(explained.page_html) if explained.page_html else None,
                    "comment": str(explained.comment_md),
                    "infographic": (str(explained.infographic) if explained.infographic else None),
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

        repo: Path | None = None
        if args.map is not None:
            used = json.loads(args.map.read_text())
        elif args.source:
            source, ref = _resolve(args.source, args.store)
            used, _, _, repo = load_map_dict(
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

        if args.board_command == "units":
            from prc.explainer.units import listing

            print(listing(used), end="")

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
        if "infographic" in board_doc:
            from prc.presentation.infographic import infobrief

            try:
                infobrief(used, used.get("brief"), board_doc)
            except ValueError as error:
                print(f"infographic: {error}", file=sys.stderr)

                return 2

        print(f"{facts['receipts']} receipts verified")

        print(
            f"~{facts['estimate_none_seconds']:.1f} s silent (voice none); guide target is 45-75 s"
        )
        print(facts["coverage_summary"])
        if "reading" in board_doc:
            from prc.explainer.units import units

            print(
                f"reading: {len(board_doc['reading'])} entries explain all "
                f"{len(units(used))} changed units"
            )
        for risk in facts["note_risks"]:
            print(f"warning: {risk}")

        if args.board_command == "preview":
            from prc.explainer import render as explain_render
            from prc.explainer.voice import NoneBackend

            out_dir = args.out / args.board.stem
            git_dir: str | None
            if args.git_dir is not None:
                git_dir = str(args.git_dir)
            else:
                git_dir = str(repo) if repo is not None and repo.exists() else None
            try:
                rendered = explain_render.render(
                    board_doc,
                    used,
                    facts,
                    out_dir,
                    NoneBackend(),
                    git_dir,
                    keys_only=True,
                )
            except explain_render.RenderError as error:
                raise SystemExit(f"prc board preview: {error}") from error
            print(f"{len(board_doc['scenes']) * 2} stills in {out_dir / 'keys'}")
            for warning in rendered.layout_warnings:
                print(f"warning: {warning}")

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

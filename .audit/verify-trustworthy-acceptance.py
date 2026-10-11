"""Verify three fixed-revision review packets through the installed package."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from prc.explainer.check import verify_board
from prc.explainer.preflight import line_coverage
from prc.explainer.render import fill
from prc.facts import compute_facts
from prc.identity import to_jsonable


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(directory: str, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "--git-dir", directory, "-c", "core.hooksPath=/dev/null", *args]
    )


def subset(expected: Any, actual: Any, location: str) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), location
        for key, value in expected.items():
            assert key in actual, f"{location}.{key} missing"
            subset(value, actual[key], f"{location}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(expected) == len(actual), location
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            subset(left, right, f"{location}[{index}]")
    else:
        assert expected == actual, f"{location}: {expected!r} != {actual!r}"


def verify(case: Path) -> dict[str, Any]:
    provenance = json.loads((case / "provenance.json").read_text())
    identity = json.loads((case / "render-identity.json").read_text())
    for name, key in (
        ("original.diff", "original_diff_sha256"),
        ("original.numstat", "original_numstat_sha256"),
        ("map.json", "map_sha256"),
        ("board.json", "board_json_sha256"),
        ("provider-resources.json", "provider-resources_json_sha256"),
        ("merge-status.json", "merge-status_json_sha256"),
    ):
        assert digest(case / name) == provenance[key], (case.name, name)
        assert digest(case / name) == identity["input_hashes"][name], (case.name, name)

    base, head = provenance["base_sha"], provenance["head_sha"]
    directory = provenance["git_dir"]
    flags = ("diff", "--no-ext-diff", "--no-textconv", "--no-renames")
    assert git(directory, *flags, "--binary", base, head) == (case / "original.diff").read_bytes()
    assert (
        git(directory, *flags, "--numstat", base, head) == (case / "original.numstat").read_bytes()
    )
    counts = {}
    for row in (case / "original.numstat").read_text().splitlines():
        added, removed, path = row.split("\t")
        counts[path] = (int(added), int(removed))

    captured = json.loads((case / "map.json").read_text())
    assert (captured["base_sha"], captured["head_sha"]) == (base, head)
    assert set(counts) == {file["path"] for file in captured["files"]}
    provider = json.loads((case / "provider-resources.json").read_text())
    assert provider["pr"]["head_sha"] == head
    assert provider["pr"]["base_tip_sha"] == base
    merge = json.loads((case / "merge-status.json").read_text())
    assert merge["head_sha"] == head
    assert merge["html_url"] == provenance["url"]
    assert merge["merged"] is True and merge["merged_at"]

    checked_lines = 0
    for file in captured["files"]:
        assert (file["added"], file["removed"]) == counts[file["path"]], file["path"]
        blobs: dict[str, list[str]] = {}
        for hunk in file["hunks"]:
            for line in hunk["lines"]:
                for key, revision in (("old", base), ("new", head)):
                    number = line[key]
                    if number is None:
                        continue
                    if key not in blobs:
                        blobs[key] = (
                            git(directory, "show", f"{revision}:{file['path']}")
                            .decode("utf-8", "replace")
                            .splitlines()
                        )
                    assert blobs[key][number - 1] == line["text"], (file["path"], key, number)
                    checked_lines += 1

    result = json.loads((case / "cli.json").read_text())
    out = Path(result["out"])
    assert out == Path(identity["out"])
    data = json.loads((out / "map.json").read_text())
    for key in (
        "pr",
        "url",
        "title",
        "author",
        "base_sha",
        "head_sha",
        "files",
        "symbols",
        "edges",
        "tour",
    ):
        assert data[key] == captured[key], (case.name, key)
    for key in ("files", "checks", "mismatches"):
        assert data["brief"][key] == captured["brief"][key], (case.name, "brief", key)
    run = json.loads((out / "run.json").read_text())
    assert run["stored_head_sha"] == head and run["live_head_sha"] is None
    assert run["map_source"] == "stored" and run["voice"] == "kokoro", run["voice"]
    assert result["check_passed"] is True
    assert not run["layout_warnings"], run["layout_warnings"]
    info = run["infographic"]
    candidates = [
        Path(identity["command"][i + 1])
        for i, value in enumerate(identity["command"][:-1])
        if value == "--infographic"
    ]
    assert [a["name"] for a in info["attempts"]] == [
        path.name for path in candidates[: len(info["attempts"])]
    ], info
    assert info["status"] == "passed", (case.name, info)
    assert (out / "infographic" / "brief.json").is_file(), case.name
    preview = json.loads((candidates[0].parent / "brief.json").read_text())
    published_brief = json.loads((out / "infographic/brief.json").read_text())
    assert preview["relations"] == published_brief["relations"], (
        case.name,
        "infographic relationships changed",
    )
    assert preview["lines"] == published_brief["lines"], (case.name, "infographic words changed")
    records = json.loads((out / "infographic/check.json").read_text())
    for index, record in enumerate(records, 1):
        expected_sha = identity["infographic_candidates"][record["name"]]
        assert record["sha256"] == expected_sha, (case.name, "candidate hash")
        assert digest(out / f"infographic/candidate-{index:02d}.png") == expected_sha, (
            case.name,
            "snapshot hash",
        )
    disclosure = "Infographic drawn by AI. Words from prc."
    comment = (out / "comment.md").read_text()
    if info["status"] == "passed":
        assert digest(out / "infographic.png") == info["published_sha256"], case.name
        assert f"![{disclosure}](infographic.png)" in comment, case.name
        page = (out / "doc.html").read_text()
        assert (
            'class="infographic"' in page
            and "data:image/png;base64," in page
            and disclosure in page
        ), case.name
        checks = json.loads((out / "infographic/check.json").read_text())
        passed = next(c for c in checks if c["sha256"] == info["published_sha256"])
        assert passed["verdict"] == "pass" and len(passed["modes"]) == 4, passed
        assert published_brief["relations"] and all(r["drawn"] for r in passed["relations"]), passed
        assert not passed["failed_modes"] and not passed["missing"] and not passed["invented"], (
            passed
        )
    else:
        assert info["status"] == ("failed" if candidates else "missing"), info
        assert not (out / "infographic.png").exists(), case.name
        assert "card.png" in comment, case.name
    for name, sha in identity["output_hashes"].items():
        assert digest(out / name) == sha, (case.name, name)
    for name in (
        "map.html",
        "video.mp4",
        "doc.html",
        "card.png",
        "comment.md",
        "board.json",
        "run.json",
    ):
        assert (out / name).is_file(), (case.name, name)

    board = json.loads((case / "board.json").read_text())
    expected = copy.deepcopy(board)
    facts = verify_board(expected, captured)
    fill(expected, captured, facts, directory)
    rendered = json.loads((out / "board.json").read_text())
    subset(expected, rendered, "board")
    cov = line_coverage(board, captured)
    assert cov["total"] == sum(added + removed for added, removed in counts.values())

    parsed = compute_facts(data)
    if case.name == "swarm-116":
        assert len(parsed.limits) == 7
        assert parsed.stats.symbols_changed == 0 and parsed.stats.tests_touched == 2
        assert all(limit.reason == "unsupported language" for limit in parsed.limits)
        for name in ("card.html", "comment.md", "map.html"):
            text = (out / name).read_text()
            assert "unsupported" in text.lower(), name
            assert "No code symbols changed" not in text, name
        assert "unsupported" in json.dumps(rendered).lower()
        assert "file-level change" in (out / "card.html").read_text()

    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height,r_frame_rate:format=duration",
                "-of",
                "json",
                str(out / "video.mp4"),
            ]
        )
    )
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "30/1")
    assert any(stream["codec_type"] == "audio" for stream in probe["streams"])
    assert abs(float(probe["format"]["duration"]) - result["duration"]) < 0.1
    sound = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "info",
            "-i",
            str(out / "video.mp4"),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    peak = float(sound.split("max_volume: ")[1].split(" dB")[0])
    assert peak > -50, (case.name, "silent narration", peak)
    for name in ("map.png", "doc.png", "video-diff.png"):
        assert (case / "screenshots" / name).is_file(), (case.name, name)
    browser = json.loads((case / "browser-check.json").read_text())
    assert browser["output_hashes"] == identity["output_hashes"], (
        case.name,
        "browser proof is stale",
    )
    assert not browser["page_errors"] and not browser["remote_requests"], browser
    assert provenance["human_reviewer"] == "user" and provenance["human_acceptance"] == "pending"
    return {
        "case": case.name,
        "base_sha": base,
        "head_sha": head,
        "facts": to_jsonable(parsed),
        "line_coverage": cov,
        "git_line_checks": checked_lines,
        "video": probe,
        "audio_peak_db": peak,
        "voice": run["voice"],
        "infographic": info,
        "render_commit": identity["prc_commit"],
        "human_acceptance": "pending",
    }


root = Path(sys.argv[1]).resolve()
package = importlib.util.find_spec("prc")
assert package and package.origin and "wheel-env" in package.origin, package
reports = [verify(root / slug) for slug in ("librarysync-98", "em-5756", "swarm-116")]
(root / "verification.json").write_text(
    json.dumps({"installed_package": package.origin, "cases": reports}, indent=2) + "\n"
)
for report in reports:
    print(
        report["case"],
        report["base_sha"][:12],
        report["head_sha"][:12],
        "verified; human acceptance pending",
    )

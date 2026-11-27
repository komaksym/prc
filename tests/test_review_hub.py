from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / ".audit" / "build-trustworthy-review.py"
SLUGS = ("librarysync-98", "em-5756", "swarm-116")
NL = "\n"


def make_records(root: Path) -> Path:
    cases = []
    for idx, slug in enumerate(SLUGS):
        case = root / slug
        out = case / "output" / (slug + "-out")
        out.mkdir(parents=True)
        (case / "provenance.json").write_text(
            json.dumps(
                {
                    "url": "https://github.com/example/" + slug,
                    "base_sha": "b" * 40,
                    "head_sha": "f" * 40,
                }
            )
        )
        (case / "cli.json").write_text(json.dumps({"out": str(out)}))
        (out / "map.json").write_text(
            json.dumps(
                {
                    "pr": "example/" + slug,
                    "title": "Demo change " + str(idx),
                    "files": [{"added": 3, "removed": 1}],
                }
            )
        )
        (out / "run.json").write_text(
            json.dumps(
                {
                    "voice": "kokoro",
                    "infographic": {"status": "passed", "attempts": [{"verdict": "pass"}]},
                }
            )
        )
        (case / "original.diff").write_text("diff --git a/" + slug + " b/" + slug + NL)
        cases.append(
            {
                "case": slug,
                "facts": {"stats": {"files": 1, "tests_touched": 0}, "limits": []},
                "line_coverage": {"shown": 1, "total": 2, "unavailable": 0},
            }
        )
    (root / "verification.json").write_text(json.dumps({"cases": cases}))
    return root


def run_builder(root: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(BUILDER), str(root)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr


def fresh_root(tmp_path: Path) -> Path:
    root = tmp_path / "acceptance"
    root.mkdir()
    return make_records(root)


def test_hub_separates_purposes_and_retires_same_pr_scoring(tmp_path: Path) -> None:
    root = fresh_root(tmp_path)
    run_builder(root)
    hub = (root / "index.html").read_text()
    lowered = hub.lower()
    assert "artifact acceptance" in lowered
    assert "matched pr evaluation" in lowered
    for bad in (
        "Score each output from 1 to 5",
        "1 adds no help",
        "Usefulness scores",
        "First review the PR on GitHub",
        "Review there first",
        "Then assess the extra help",
        "Then use the PRC outputs",
        "Rate each output from 1 to 5",
        "Inspect direction, arrowheads",
    ):
        assert bad not in hub, bad
    assert "excluded from the unseen" in lowered
    for slug in SLUGS:
        assert slug in hub
    assert "color-scheme:light" in hub
    assert "Agent verification runs before human acceptance" in hub
    assert "verification.json" in hub
    assert "GitHub plus Coldtea PR Lens CI" in hub
    assert "GitHub plus PRC" in hub
    assert "review artifact acceptance before" not in lowered
    assert "optional fact-check" in lowered
    assert "raw diff is optional" in lowered
    assert "two similar, distinct prs that you have not seen" in lowered
    assert "review each pr once, in its assigned condition" in lowered
    assert "randomize which pr receives prc" in lowered
    assert "freeze equivalent questions" in lowered
    assert "compare equivalent question scores per pair" in lowered
    assert "study is in preparation" in lowered
    assert "no sealed study roster" in lowered
    assert "reconcile and freeze" in lowered
    assert "distinct unseen" in lowered
    assert "does not prove arrow direction" in lowered


def test_fresh_worksheet_has_both_purposes_and_no_scores(tmp_path: Path) -> None:
    root = fresh_root(tmp_path)
    run_builder(root)
    sheet = (root / "acceptance.md").read_text()
    lowered = sheet.lower()
    assert "artifact acceptance" in lowered
    assert "matched pr evaluation" in lowered
    assert "excluded from the unseen" in lowered
    for bad in (
        "Usefulness scores (1 to 5)",
        "Score each output",
        "Rate each output",
        "First review the PR on GitHub",
        "Extra help from PRC:",
    ):
        assert bad not in sheet, bad
    for slug in SLUGS:
        assert "## " + slug in sheet
    assert "Decision: pending." in sheet
    assert "Broken references:" in sheet
    assert "optional fact-check" in lowered


def old_seed_text() -> str:
    lines = [
        "# Human acceptance",
        "",
        "You are the only human reviewer.",
        "",
        "## Review method",
        "",
        "Use the normal GitHub PR page in your browser as the baseline.",
        "First review the PR on GitHub and record what you understand and what remains unclear.",
        "Then use the PRC outputs, including the infographic and record what they add to your review.",
        "",
        "Score each output for the extra help it adds beyond the GitHub baseline.",
        "",
        "| Score | Extra help from PRC |",
        "| --- | --- |",
        "| 1 | No extra help, or adds confusion. |",
        "| 2 | Small benefit. |",
        "| 3 | Useful extra context. |",
        "| 4 | Clearly improves understanding and guides review. |",
        "| 5 | Substantial extra help; I would choose to use it again. |",
        "",
        "## librarysync-98",
        "",
        "Listening check: passed. Both recognizers heard every code name. Record tone problems you hear.",
        "",
        "GitHub baseline: https://github.com/example/librarysync-98",
        "",
        "Does the explanation make the episode ordering change clear?",
        "",
        "Decision: pending.",
        "",
        "Factual errors: found a wrong count in the card.",
        "",
        "GitHub baseline notes: my baseline note stays.",
        "",
        "Usefulness scores (1 to 5): card 4; comment pending.",
        "",
        "Extra help from PRC: it helped me see the callers.",
        "",
        "Most useful / least useful output: the map.",
        "",
        "Would use PRC for this PR (yes/no and why): yes, because of the callers.",
        "",
        "Useful for reviewing this PR: awaiting your review.",
        "",
        "## em-5756",
        "",
        "Decision: pending.",
        "",
        "Factual errors: awaiting your review.",
        "",
        "## swarm-116",
        "",
        "Decision: pending.",
        "",
        "Factual errors: awaiting your review.",
        "",
    ]
    return NL.join(lines)


def test_existing_notes_survive_regeneration_without_old_scoring(tmp_path: Path) -> None:
    root = fresh_root(tmp_path)
    (root / "acceptance.md").write_text(old_seed_text())
    run_builder(root)
    sheet = (root / "acceptance.md").read_text()
    lowered = sheet.lower()
    assert "found a wrong count in the card." in sheet
    assert "my baseline note stays." in sheet
    assert "card 4; comment pending." in sheet
    assert "it helped me see the callers." in sheet
    assert "yes, because of the callers." in sheet
    assert "Legacy acceptance note" in sheet
    assert "Listening check: passed." in sheet
    assert "Does the explanation make the episode ordering change clear?" in sheet
    assert "GitHub PR: https://github.com/example/librarysync-98" in sheet
    for bad in (
        "Usefulness scores (1 to 5)",
        "Extra help from PRC:",
        "Most useful",
        "Would use PRC",
        "First review the PR on GitHub",
        "Score each output",
        "No extra help, or adds confusion.",
        "Small benefit.",
        "Substantial extra help;",
        "| --- |",
    ):
        assert bad not in sheet, bad
    assert "artifact acceptance" in lowered
    assert "matched pr evaluation" in lowered
    assert "Broken references:" in sheet
    run_builder(root)
    again = (root / "acceptance.md").read_text()
    assert "found a wrong count in the card." in again
    assert "my baseline note stays." in again
    assert again == sheet

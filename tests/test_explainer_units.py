"""Reading units and the reading path check: every changed piece gets one plain entry."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from prc.explainer.check import reading_problems
from prc.explainer.units import key, units

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tests/data/explainer/maps/pr12.json"
CODE = "src/linkedin_mdp_mcp/invitation_shortlist.py"
TESTS = "tests/e2e_invitation_shortlist.py"


def _map() -> dict[str, Any]:
    return json.loads(MAP.read_text())  # type: ignore[no-any-return]


def _changed(m: dict[str, Any]) -> Counter[tuple[str, str]]:
    return Counter(
        (f["path"], key(ln))
        for f in m["files"]
        for h in f["hunks"]
        for ln in h["lines"]
        if ln["op"] in ("+", "-") and ln["text"].strip()
    )


def test_every_changed_line_belongs_to_exactly_one_unit() -> None:
    m = _map()
    seen = Counter((u["path"], key(ln)) for u in units(m) for ln in u["lines"])
    assert seen == _changed(m)
    assert max(seen.values()) == 1


def test_symbols_become_units_and_leftover_lines_a_module_unit() -> None:
    by_id = {u["id"]: u for u in units(_map())}
    date_added = by_id[f"{CODE}::_date_added"]
    assert (date_added["role"], date_added["kind"], date_added["status"]) == (
        "code",
        "function",
        "added",
    )
    assert date_added["line"] == 441 and not date_added["removed"]
    assert by_id[f"{TESTS}::<module>"]["kind"] == "module"
    assert (
        by_id[f"{TESTS}::test_missing_date_added_stays_unknown_and_does_not_change_membership"][
            "kind"
        ]
        == "test"
    )
    assert by_id["PLANS.md"]["role"] == "docs"
    assert by_id["infographic/prospect-date-added/infographic.png"]["lines"] == []


def test_workflow_splits_into_settings_jobs_and_named_steps() -> None:
    text = [
        "name: nightly",
        "on:",
        "  schedule:",
        "    - cron: '0 3 * * *'",
        "jobs:",
        "  sync:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - name: Run sync",
        "        run: uv run python scripts/sync.py",
    ]
    lines = [{"op": "+", "new": n, "old": None, "text": t} for n, t in enumerate(text, 1)]
    m = {
        "files": [
            {
                "path": ".github/workflows/nightly.yml",
                "status": "added",
                "kind": "config",
                "hunks": [{"old_start": 0, "new_start": 1, "lines": lines}],
            }
        ],
        "symbols": [],
    }
    found = {u["name"]: [ln["new"] for ln in u["lines"]] for u in units(m)}
    assert found == {
        "settings": [1, 2, 3, 4, 5],
        "job sync": [6, 7, 8],
        "step actions/checkout@v4": [9],
        "step Run sync": [10, 11],
    }
    assert {u["role"] for u in units(m)} == {"ci"}


def _complete(m: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per code or CI unit, one shared entry per test, docs or data role."""
    reading: list[dict[str, Any]] = []
    shared: dict[str, list[str]] = {}
    for u in units(m):
        if u["role"] in ("test", "docs", "data"):
            shared.setdefault(u["role"], []).append(u["id"])
        else:
            reading.append({"units": [u["id"]], "say": "The change adds this part."})
    for ids in shared.values():
        reading.append({"units": ids, "say": ["The pull request updates these files."]})
    return reading


def test_complete_reading_path_passes() -> None:
    m = _map()
    assert reading_problems({"reading": _complete(m)}, m) == []


def _broken(m: dict[str, Any], how: str) -> list[dict[str, Any]]:
    reading = _complete(m)
    if how == "missing":
        reading.pop(0)
    elif how == "duplicate":
        reading.append({"units": reading[0]["units"], "say": "The change adds this part."})
    elif how == "unknown":
        reading[0]["units"] = ["src/nowhere.py::ghost"]
    elif how == "mixed":
        reading[0]["units"] = reading[0]["units"] + [f"{TESTS}::<module>"]
        for e in reading[1:]:
            e["units"] = [x for x in e["units"] if x != f"{TESTS}::<module>"]
    elif how == "cross-file":
        reading[0]["units"] = reading[0]["units"] + [
            "artifacts/invitation-shortlist-e2e-evidence.json"
        ]
        reading = [e for e in reading if e["units"]]
    elif how == "passive":
        reading[0]["say"] = "The value is computed by the helper."
    elif how == "three sentences":
        reading[0]["say"] = ["The helper reads the date.", "It checks the source.", "It returns."]
    return reading


@pytest.mark.parametrize(
    ("how", "want"),
    [
        ("missing", "units with no reading sentence"),
        ("duplicate", "is already explained in reading 0"),
        ("unknown", "is not a unit of this pull request"),
        ("mixed", "mixes code, test units"),
        ("cross-file", "mixes code, data units"),
        ("passive", "uses the passive"),
        ("three sentences", "say needs one or two sentences"),
    ],
)
def test_broken_reading_path_names_the_problem(how: str, want: str) -> None:
    m = _map()
    problems = reading_problems({"reading": _broken(m, how)}, m)
    assert any(want in p for p in problems), problems


def _five_functions() -> dict[str, Any]:
    lines = [{"op": "+", "new": n, "old": None, "text": f"def f{n}(): pass"} for n in range(1, 6)]
    one = [{"op": "+", "new": 1, "old": None, "text": "VALUE = 1"}]
    return {
        "files": [
            {"path": "a.py", "status": "added", "kind": "code", "hunks": [{"new_start": 1, "lines": lines}]},
            {"path": "b.py", "status": "added", "kind": "code", "hunks": [{"new_start": 1, "lines": one}]},
        ],
        "symbols": [
            {"id": f"a.py::f{ln['new']}", "path": "a.py", "qualname": f"f{ln['new']}", "kind": "function",
             "status": "added", "hunks": [{"lines": [ln]}]}
            for ln in lines
        ],
    }  # fmt: skip


def test_code_entries_stay_in_one_file_and_hold_at_most_four_units() -> None:
    m = _five_functions()
    say = "The change adds these functions."
    five = [f"a.py::f{n}" for n in range(1, 6)]
    too_many = reading_problems(
        {"reading": [{"units": five, "say": say}, {"units": ["b.py"], "say": say}]}, m
    )
    assert any("joins 5 units" in p for p in too_many), too_many
    split = [{"units": five[:4], "say": say}, {"units": [five[4], "b.py"], "say": say}]
    cross = reading_problems({"reading": split}, m)
    assert any("joins units from 2 files" in p for p in cross), cross
    fine = [
        {"units": five[:4], "say": say},
        {"units": [five[4]], "say": say},
        {"units": ["b.py"], "say": say},
    ]
    assert reading_problems({"reading": fine}, m) == []


def test_cli_lists_units_with_their_ids(capsys: pytest.CaptureFixture[str]) -> None:
    from prc.cli import main

    assert main(["board", "units", "--map", str(MAP)]) == 0
    out = capsys.readouterr().out
    assert f"{CODE}::_date_added\n    code function added, 37 changed lines, {CODE}:441" in out

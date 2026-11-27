"""The hub handoff expects as many PR sections as the roster lists."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load_handoff() -> ModuleType:
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "handoff_study_hub", REPO / "scripts" / "handoff_study_hub.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_three_entry_roster_expects_three_prs(tmp_path: Path) -> None:
    roster = [{"id": f"v4-{c}", "pr_identity": f"o/r#{i}"} for i, c in enumerate("abc")]
    (tmp_path / "roster.json").write_text(json.dumps(roster), encoding="utf-8")
    assert _load_handoff()._expected_pr_count(tmp_path) == 3


def test_missing_roster_refuses_the_handoff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        _load_handoff()._expected_pr_count(tmp_path)
    assert exc.value.code == 1
    assert "HANDOFF REFUSED" in capsys.readouterr().err

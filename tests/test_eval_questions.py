"""Question files validate under both frozen v1 and corrected v2 versions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "eval_validate", ROOT / "scripts/eval/validate_questions.py"
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
validate_file = _mod.validate_file


@pytest.mark.parametrize(
    ("filename", "version", "expected"),
    [
        ("pr12.json", 1, []),
        ("pr12.v2.json", 2, []),
        ("pr12.json", 2, ["pr12.json: version must be 1"]),
        ("pr12.v2.json", 1, ["pr12.v2.json: version must be 2"]),
    ],
)
def test_question_version_matches_its_dataset(
    tmp_path: Path, filename: str, version: int, expected: list[str]
) -> None:
    path = tmp_path / filename
    path.write_text(json.dumps({"version": version}))
    assert [error for error in validate_file(path) if "version must be" in error] == expected

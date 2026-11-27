from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prc import pipeline
from prc.fixture_source import FixtureSource
from prc.identity import sha256_hex
from prc.model import PrRef
from prc.presentation import infographic as gate
from prc.verification import EligibilityPolicy
from test_infographic import blank_png

ROOT = Path(__file__).resolve().parents[1]


def test_explain_gates_an_immutable_snapshot_and_records_readings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = blank_png(tmp_path / "candidate.png")
    captured = candidate.read_bytes()
    data = ROOT / "tests/data/explainer/maps/pr12.json"

    def check(path: Path, brief: gate.InfographicBrief) -> gate.GateDecision:
        candidate.write_bytes(b"changed while OCR ran")
        assert path.read_bytes() == captured
        return gate.GateDecision("pass", (), (), {"modes": {"psm-3": 18}, "failed_modes": []})

    def card(*args: Any) -> None:
        args[-2].write_text("card")
        args[-1].write_bytes(captured)

    monkeypatch.setattr(gate, "gate", check)
    monkeypatch.setattr(pipeline, "render_pr_card", card)
    result = pipeline.run_explain(
        FixtureSource(repo=tmp_path, resources={}),
        PrRef("acme", "shop", 1),
        lambda: 0.0,
        EligibilityPolicy(),
        tmp_path / "out",
        map_path=data,
        voice="none",
        infographics=(candidate,),
    )
    assert (result.out_dir / "infographic.png").read_bytes() == captured
    checks = json.loads((result.out_dir / "infographic/check.json").read_text())
    assert checks[0]["sha256"] == sha256_hex(captured)
    assert checks[0]["modes"] == {"psm-3": 18}
    assert checks[0]["failed_modes"] == []
    assert "Upload `infographic.png`" in (result.out_dir / "comment.md").read_text()

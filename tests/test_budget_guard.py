"""Redline guard keeps metered runs from burning to zero mid-flight.

Past mistakes replayed here: dispatching at 4 pct with no gate (burn to
zero, cf. 2026-10-11 omitted-model dispatch); losing the queued units on
retry (overwritten run logs in the release audit); resuming from a stale
checkpoint without a loud failure (stale-mirror class).
Every test binds a non-empty return, so a function that returns nothing
fails here instead of passing silently.
"""

from __future__ import annotations

from pathlib import Path

from prc import budget_guard
from prc.budget_guard import BudgetGuard, BudgetSnapshot


def _guard(
    remaining: float, path: Path, reset_at: float | None = None
) -> BudgetGuard:
    return BudgetGuard(
        lambda: BudgetSnapshot(remaining_fraction=remaining, reset_at=reset_at),
        path,
    )


def test_redline_boundary_is_checkable(tmp_path: Path) -> None:
    assert _guard(0.05, tmp_path / "c.json").can_dispatch() is False
    assert _guard(0.0501, tmp_path / "c.json").can_dispatch() is True
    assert _guard(0.0, tmp_path / "c.json").can_dispatch() is False


def test_burn_to_zero_dispatch_is_rejected(tmp_path: Path) -> None:
    guard = _guard(0.04, tmp_path / "c.json")
    errors = guard.gate()
    assert errors, "dispatch at 4 pct must never go"
    assert any("BudgetGuard.checkpoint" in e for e in errors)
    assert any("BudgetGuard.resume" in e for e in errors)


def test_healthy_meter_dispatches_clean(tmp_path: Path) -> None:
    guard = _guard(0.42, tmp_path / "c.json")
    assert guard.can_dispatch() is True
    assert guard.gate() == []


def test_checkpoint_roundtrip_restores_queue(tmp_path: Path) -> None:
    path = tmp_path / "redline.json"
    guard = _guard(0.04, path)
    out = guard.checkpoint(("unit-b", "unit-c"), ["unit-a"])
    assert out == path and path.exists()
    restored = guard.load_checkpoint()
    assert restored.queued == ("unit-b", "unit-c")
    assert restored.done == ("unit-a",)
    assert restored.checkpoint_id, "checkpoint must carry a non-empty id"


def test_checkpoint_return_is_never_empty(tmp_path: Path) -> None:
    guard = _guard(0.03, tmp_path / "r.json")
    out = guard.checkpoint([], [])
    assert str(out), "checkpoint must return its path"
    loaded = guard.load_checkpoint()
    assert loaded.checkpoint_id.strip() != ""


def test_resume_while_red_raises_instead_of_silent_go(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    _guard(0.04, path).checkpoint(["unit-b"], [])
    try:
        _guard(0.02, path).resume()
    except RuntimeError as exc:
        assert "BudgetGuard.resume" in str(exc)
    else:
        raise AssertionError("resume while red must raise, never drift on")


def test_resume_after_reset_restores_every_queued_unit(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    _guard(0.04, path).checkpoint(["unit-b", "unit-c"], ["unit-a"])
    restored = _guard(0.61, path).resume()
    assert restored.queued == ("unit-b", "unit-c")
    assert restored.done == ("unit-a",)


def test_stale_schema_fails_naming_the_fix(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text(
        '{"schema": "budget-guard/v0", "queued": [], "done": []}',
        encoding="utf-8",
    )
    try:
        _guard(0.61, path).load_checkpoint()
    except ValueError as exc:
        assert "BudgetGuard.checkpoint" in str(exc)
    else:
        raise AssertionError("stale schema must fail loudly")


def test_reset_needs_recovery_above_redline() -> None:
    red = BudgetSnapshot(remaining_fraction=0.04)
    fresh = BudgetSnapshot(remaining_fraction=0.61)
    still_red = BudgetSnapshot(remaining_fraction=0.02)
    assert budget_guard.is_reset(red, fresh) is True
    assert budget_guard.is_reset(red, still_red) is False
    assert budget_guard.is_reset(fresh, fresh) is False


def test_threshold_lives_only_in_budget_guard() -> None:
    source = Path(budget_guard.__file__ or "").read_text(encoding="utf-8")
    assert "0.05" in source
    assert "budget-guard/v1" in source

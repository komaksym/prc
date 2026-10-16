"""Guard keeps the notes-hub browser pass required for hub handoffs."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
RECIPE = REPO / ".agents" / "skills" / "verify" / "features" / "notes.md"
DRIVER = REPO / "scripts" / "verify_notes_hub.py"
INDEX = REPO / ".agents" / "skills" / "verify" / "features" / "README.md"
SKILL = REPO / ".agents" / "skills" / "verify" / "SKILL.md"
CONTROLS = (
    "GitHub",
    "infographic",
    "video",
    "page.html",
    "judge vote",
)


def test_recipe_requires_driver_pass() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/verify_notes_hub.py" in text
    assert "PASS" in text
    assert "checks.json" in text
    assert "paired-study/private" not in text


def test_recipe_lists_every_pr_control() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    for control in CONTROLS:
        assert control in text, f"notes.md must list {control}"


def test_recipe_forbids_old_study_content() -> None:
    text = RECIPE.read_text(encoding="utf-8").lower()
    assert "no questions" in text or "questions" in text
    assert "notes.json" in text
    assert "verdict" in text
    assert "updated_at" not in text
    assert "notes box" not in text
    assert "data-notes-id" not in text


def test_driver_covers_every_control_and_evidence() -> None:
    text = DRIVER.read_text(encoding="utf-8")
    for control in ("github", "infographic", "currentTime", "page", "verdict"):
        assert control.lower() in text.lower(), f"driver must cover {control}"
    assert "checks.json" in text
    assert "cleanup" in text.lower()
    assert "agent-browser" in text
    assert "/api/notes" not in text
    assert "data-notes-id" not in text
    assert os.access(DRIVER, os.X_OK), "driver must stay executable"


def test_skill_index_points_to_recipe() -> None:
    assert "notes.md" in INDEX.read_text(encoding="utf-8")
    assert "verify_notes_hub" in SKILL.read_text(encoding="utf-8")


HANDOFF = REPO / "scripts" / "handoff_study_hub.py"


def test_handoff_recipe_requires_supervised_handoff() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/handoff_study_hub.py" in text
    assert "artifacts/study-v3/handoff/notes" in text
    lowered = text.lower()
    assert "pidfile" in lowered
    assert "exact url" in lowered
    assert "supervised" in lowered


def test_skill_drive_requires_handoff_record() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "handoff_study_hub" in text
    assert "artifacts/study-v3/handoff/notes" in text
    lowered = text.lower()
    assert "exact url" in lowered
    assert "pidfile" in lowered or "supervised" in lowered


def test_handoff_script_meets_contract() -> None:
    assert HANDOFF.is_file(), "handoff script is missing"
    text = HANDOFF.read_text(encoding="utf-8")
    assert "start_new_session" in text or "setsid" in text
    assert "nohup" in text.lower()
    assert "pidfile" in text.lower()
    assert "silent" in text.lower()
    assert "preconnect" in text.lower()
    assert "notes.json" in text
    assert "notes-review" in text
    assert "--stop" in text
    assert "artifacts/study-v3/handoff/notes" in text
    assert "agent-browser" in text
    assert "HANDOFF REFUSED" in text
    for field in ('"url"', '"port"', '"pid"', '"pidfile"', '"screenshot"', '"checks"'):
        assert field in text
    assert os.access(HANDOFF, os.X_OK), "handoff script must stay executable"


@pytest.mark.parametrize("suffix", ["", "/"])
def test_live_pass_puts_operator_verdict_back_when_a_check_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    """2026-10-16: a live pass left a test verdict in the real hub and skipped cleanup.

    The second run uses the hub URL as the handoff record prints it, with a
    trailing slash: the restore then sent Origin "http://host:port/", the hub
    refused it with 403, and the test verdict stayed in the operator's hub.
    Notes now live in chat; the hub only stores judge votes.
    """
    import importlib.util
    import shutil
    import sys
    import threading

    sys.path.insert(0, str(REPO / "src"))
    from prc.evaluation import notes as notes_mod

    spec = importlib.util.spec_from_file_location("verify_notes_hub", DRIVER)
    assert spec and spec.loader
    drv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(drv)
    source = REPO / "artifacts" / "output-v5" / "notes"
    for name in ("roster.json", "prepared_root", "spotcheck.json"):
        shutil.copy(source / name, tmp_path / name)
    httpd, url = notes_mod.serve(tmp_path)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        state = drv.api_get(url, "/api/state")
        first_spot = state["spotcheck"][0]["id"]
        drv.api_post(url, "/api/verdict", {"id": first_spot, "verdict": "wrong"})
        before = drv.api_get(url, "/api/state")

        class TypesThenFails:
            def __init__(self, session: str) -> None:
                self.session = session

            def run(self, *args: str) -> str:
                drv.api_post(url, "/api/verdict", {"id": first_spot, "verdict": ""})
                raise drv.Fail("browser died mid-pass")

        class Done:
            stdout = "verifynotes-test"

        monkeypatch.setattr(drv, "Browser", TypesThenFails)
        monkeypatch.setattr(drv.subprocess, "run", lambda *a, **k: Done())
        with pytest.raises(drv.Fail, match="browser died"):
            drv.check_hub(url + suffix, tmp_path, True)
        after = drv.api_get(url, "/api/state")
        assert after["verdicts"] == before["verdicts"] == {first_spot: "wrong"}
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_live_mode_always_restores_verdicts() -> None:
    text = DRIVER.read_text(encoding="utf-8")
    assert "opts.cleanup_notes or bool(opts.url)" in text
    assert '"right" if spot and prior_verdicts.get(spot[0]["id"]) == "wrong" else "wrong"' in text

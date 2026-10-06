"""Skill install (claude/codex) and doctor output. Writes only under tmp_path."""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from prc import cli
from prc.explainer import doctor

SENTINEL_TOKEN = "ghp_TESTSENTINEL9x8y7z"


def _install(*argv: str) -> int:
    return cli.main(["skill", "install", *argv])


def test_install_claude_copies_skill(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from prc import skill

    assert _install("claude", "--dest", str(tmp_path)) == 0

    written = tmp_path / "prc-explain" / "SKILL.md"
    assert written.is_file()
    assert written.read_text() == skill.skill_source().read_text()
    assert str(written) in capsys.readouterr().out


def test_install_claude_reinstall_is_clean(tmp_path: Path) -> None:
    assert _install("claude", "--dest", str(tmp_path)) == 0
    assert _install("claude", "--dest", str(tmp_path)) == 0

    assert [p for p in (tmp_path / "prc-explain").iterdir()] == [
        tmp_path / "prc-explain" / "SKILL.md"
    ]


def test_install_codex_writes_agents_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _install("codex", "--dest", str(tmp_path)) == 0

    written = tmp_path / "AGENTS.md"
    assert written.is_file()
    text = written.read_text()
    assert "prc-explain" in text
    assert "prc board check" in text
    assert str(written) in capsys.readouterr().out


def test_install_codex_preserves_existing_file_and_stays_idempotent(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# My project\n\nNotes.\n")

    assert _install("codex", "--dest", str(tmp_path)) == 0
    assert _install("codex", "--dest", str(tmp_path)) == 0

    text = agents.read_text()
    assert text.startswith("# My project\n\nNotes.\n")
    assert text.count("prc-explain:start") == 1
    assert text.count("prc-explain:end") == 1


def test_install_without_dest_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    assert _install("claude") == 2
    assert not (tmp_path / ".claude").exists()
    assert list(tmp_path.iterdir()) == []


def test_install_without_dest_yes_uses_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("y\n"))

    assert _install("claude") == 0
    assert (tmp_path / ".claude" / "skills" / "prc-explain" / "SKILL.md").is_file()


def test_install_rejects_unknown_agent() -> None:
    with pytest.raises(SystemExit):
        _install("cursor", "--dest", ".")


def test_skill_text_follows_the_nine_plan_steps() -> None:
    from prc import skill

    text = skill.skill_source().read_text()
    for step in range(1, 10):
        assert re.search(rf"^##?\s*{step}\.", text, re.MULTILINE), f"step {step}"

    for anchor in (
        "prc explain --source",
        "prc board guide",
        "prc board show",
        "prc board check",
        "prc board coverage",
        "--board",
        "posted nothing",
    ):
        assert anchor in text, anchor


def test_doctor_reports_each_dependency_with_ok_or_missing() -> None:
    lines = doctor.report().splitlines()
    joined = "\n".join(lines).lower()

    for name in ("python", "ffmpeg", "chromium", "voice", "github_token"):
        assert name in joined, name

    assert lines, "one line per dependency"
    for line in lines:
        assert "ok" in line or "missing" in line or "set" in line or "unset" in line, line


def test_doctor_missing_tools_name_the_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert "brew install ffmpeg" in doctor._ffmpeg()

    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    assert "playwright install chromium" in doctor._chromium()


def test_doctor_never_prints_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", SENTINEL_TOKEN)
    report = doctor.report()

    assert SENTINEL_TOKEN not in report
    assert "GITHUB_TOKEN set" in report

    monkeypatch.delenv("GITHUB_TOKEN")
    assert "GITHUB_TOKEN unset" in doctor.report()


def test_doctor_command_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["doctor"]) == 0
    assert "GITHUB_TOKEN" in capsys.readouterr().out


def test_installed_skill_matches_board_tool_names(tmp_path: Path) -> None:
    assert _install("claude", "--dest", str(tmp_path)) == 0

    text = (tmp_path / "prc-explain" / "SKILL.md").read_text()
    assert "prc board find" in text
    assert "`prc doctor`" in text


def test_skill_source_lives_beside_the_installer() -> None:
    from prc import skill

    assert skill.skill_source().parent == Path(skill.__file__).parent

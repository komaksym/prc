from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OUTPUTS = ("map.html", "video.mp4", "doc.html", "card.png", "comment.md")
EVIDENCE_FILES = ("map.json", "board.json", "run.json")


def _isolated_copy_program() -> str:
    script = (ROOT / "scripts/verify-release.sh").read_text()
    blocks: list[str] = []
    parts = script.split("<<'PY'")
    for part in parts[1:]:
        lines = part.splitlines()
        end = None
        for i, line in enumerate(lines):
            if line == "PY":
                end = i
                break
        if end is None:
            continue
        blocks.append(chr(10).join(lines[:end]))
    for block in blocks:
        if "ls-files" in block and "checkout" in block and "shutil.copy" in block:
            return block
    raise AssertionError("isolated copy program not found")


def _run_exact_isolated_copy(repo: Path, dest: Path) -> None:
    code = _isolated_copy_program()
    proc = subprocess.run(
        [sys.executable, "-", str(repo), str(dest)],
        input=code,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr


def _claude_text() -> str:
    return (ROOT / "src/prc/skill/SKILL.md").read_text()


def test_d14_canonical_lists_five_product_outputs() -> None:
    for name in PRODUCT_OUTPUTS:
        assert name in _claude_text(), "canonical SKILL.md omits " + name


def test_d14_claude_has_single_consistent_output_list() -> None:
    text = _claude_text()
    step7 = text.split("## 7.", 1)[1].split("## 8.", 1)[0]
    for name in PRODUCT_OUTPUTS:
        assert name in step7, "SKILL.md step 7 omits product output " + name
    for name in EVIDENCE_FILES:
        assert name in step7, "SKILL.md step 7 omits evidence file " + name


def test_d14_canonical_checked_scope_is_accurate() -> None:
    text = _claude_text()
    assert "checks every fact" not in text, "canonical overclaims: checks every fact"
    assert "cited code and explicit numeric assertions" in text


def test_d14_codex_body_reflects_canonical_edits(monkeypatch: pytest.MonkeyPatch) -> None:
    from prc import skill

    sentinel = "SENTINEL_CANONICAL_EDIT_9f3k"
    base = skill._canonical_text()
    assert sentinel not in skill.codex_section()
    monkeypatch.setattr(skill, "_canonical_text", lambda: base + "\n" + sentinel + "\n")
    assert sentinel in skill.codex_section(), "codex body is not derived from SKILL.md"


def test_d14_installed_agents_share_exact_body(tmp_path: Path) -> None:
    from prc import skill
    from prc.skill import SECTION_END, SECTION_START

    claude_file = skill.install_claude(tmp_path / "c")
    codex_file = skill.install_codex(tmp_path / "x")
    installed_claude = claude_file.read_text()
    section = codex_file.read_text()
    body = section.split(SECTION_START, 1)[1].split(SECTION_END, 1)[0]
    assert body.strip() == skill.codex_body_for(installed_claude).strip()


def test_d14_codex_body_has_no_frontmatter() -> None:
    from prc import skill

    for line in skill.codex_section().splitlines():
        assert line.strip() != "---", "YAML frontmatter leaked into Codex section"


def test_d16_verify_defaults_online_without_warm_cache() -> None:
    script = (ROOT / "scripts/verify-release.sh").read_text()
    has_mode = ('"$@"' in script) or ("OFFLINE" in script)
    assert has_mode, "verify-release.sh has no explicit offline-mode handling"
    bad = []
    for ln in script.splitlines():
        s = ln.strip()
        if s.startswith("uv ") and "--offline" in s and "OFFLINE" not in s and "$" not in s:
            bad.append(s)
    assert not bad, "verify-release.sh requires a warm cache by default: " + str(bad)


def test_d16_verify_offline_mode_has_real_cache_prerequisite() -> None:
    script = (ROOT / "scripts/verify-release.sh").read_text().lower()
    assert "offline" in script, "no explicit offline mode"
    assert "warm" in script or "cache" in script, "no cache prerequisite mentioned"
    assert "uv cache" in script or "cache dir" in script, "offline mode must check a real uv cache"


def test_d16_verify_uses_cached_chromium_without_downloads() -> None:
    script = (ROOT / "scripts/verify-release.sh").read_text()
    assert "PLAYWRIGHT_BROWSERS_PATH" in script, "verifier must use the cached Chromium path"
    assert "playwright install" not in script, "verifier must not download browsers"


def test_d16_isolated_copy_keeps_tracked_and_staged_excludes_untracked(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / ".gitignore").write_text("*.bin")
    (repo / "pkg").mkdir()
    (repo / "pkg" / "keep.py").write_text("KEEP = 1")
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore", "pkg/keep.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "base"], check=True)
    (repo / "pkg" / "staged.py").write_text("STAGED = 1")
    subprocess.run(["git", "-C", str(repo), "add", "pkg/staged.py"], check=True)
    (repo / "scratch.py").write_text("SCRATCH = 1")
    (repo / "notes.json").write_text("{}")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_release_scratch.py").write_text("X = 1")
    (repo / "docs" / "media").mkdir(parents=True)
    (repo / "docs" / "media" / "keep.bin").write_text("bin")
    (repo / "eval" / "runs" / "2026-10-06-full").mkdir(parents=True)
    (repo / "eval" / "runs" / "2026-10-06-full" / "data.json").write_text("{}")
    dest = tmp_path / "checkout"
    dest.mkdir()
    _run_exact_isolated_copy(repo, dest)
    assert (dest / "pkg" / "keep.py").is_file(), "tracked file missing"
    assert (dest / "pkg" / "staged.py").is_file(), "staged file missing"
    assert not (dest / "scratch.py").exists(), "untracked scratch.py leaked"
    assert not (dest / "notes.json").exists(), "untracked json leaked"
    assert not (dest / "tests" / "test_release_scratch.py").exists(), "untracked glob match leaked"
    assert (dest / "docs" / "media" / "keep.bin").is_file(), "explicit asset missing"
    assert (dest / "eval" / "runs" / "2026-10-06-full" / "data.json").is_file(), (
        "explicit fixture missing"
    )


def test_d16_wheel_install_uses_locked_requirements() -> None:
    script = (ROOT / "scripts/verify-release.sh").read_text()
    assert "uv export" in script, "wheel install is not fed from locked dependencies"
    assert "--requirement" in script, "wheel install must pin locked requirements"

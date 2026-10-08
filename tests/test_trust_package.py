"""Trust-package regressions: D14 single-source instructions, D16 clean-cache verify.

Scope: src/prc/skill/*, scripts/verify-release.sh, release packaging.
D14 is proven behaviorally: the Codex body is derived from the canonical
SKILL.md, so consistency holds by construction instead of by parallel
string assertions.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OUTPUTS = ("map.html", "video.mp4", "doc.html", "card.png", "comment.md")
EVIDENCE_FILES = ("map.json", "board.json", "run.json")


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


def test_d14_codex_body_reflects_canonical_edits(monkeypatch) -> None:
    from prc import skill

    sentinel = "SENTINEL_CANONICAL_EDIT_9f3k"
    base = skill._canonical_text()
    assert sentinel not in skill.codex_section()
    monkeypatch.setattr(skill, "_canonical_text", lambda: base + "\n" + sentinel + "\n")
    assert sentinel in skill.codex_section(), "codex body is not derived from SKILL.md"


def test_d14_installed_agents_share_exact_body(tmp_path) -> None:
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


def test_d16_verify_copies_untracked_test_fixtures() -> None:
    import re

    script = (ROOT / "scripts/verify-release.sh").read_text()
    assert re.search(r"ls-files.*--others", script), (
        "verifier default copy misses intended untracked .py/.json fixtures"
    )


def test_d16_wheel_install_uses_locked_requirements() -> None:
    script = (ROOT / "scripts/verify-release.sh").read_text()
    assert "uv export" in script, "wheel install is not fed from locked dependencies"
    assert "--requirement" in script, "wheel install must pin locked requirements"

"""Board-writer skill installers for Claude and Codex.

SKILL.md beside this module is the canonical instruction source. Both
installed outputs derive from it: the Claude installer ships the file,
and codex_section() renders the same body minus its YAML frontmatter.
"""

from __future__ import annotations

from pathlib import Path

SKILL_NAME = "prc-explain"
SECTION_START = "<!-- prc-explain:start -->"
SECTION_END = "<!-- prc-explain:end -->"

PRODUCT_OUTPUTS = ("map.html", "video.mp4", "doc.html", "card.png", "comment.md")


def skill_source() -> Path:
    """The SKILL.md shipped inside this package."""
    return Path(__file__).resolve().parent / "SKILL.md"


def _canonical_text() -> str:
    return skill_source().read_text()


def codex_body_for(canonical: str) -> str:
    """The Codex section body derived from canonical SKILL.md text."""
    lines = canonical.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1 :]
                break
    return "\n".join(lines).strip() + "\n"


def default_skills_dir() -> Path:
    """Where Claude skills live. The caller's own configuration."""
    return Path.home() / ".claude" / "skills"


def default_dest(agent: str) -> Path:
    """The folder the installer suggests when ``--dest`` is omitted."""
    if agent == "codex":
        return Path.cwd()

    return default_skills_dir()


def install_claude(dest: Path) -> Path:
    """Copy SKILL.md to ``dest/prc-explain/SKILL.md``. Returns the path written."""
    written = dest / SKILL_NAME / "SKILL.md"
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text(_canonical_text())

    return written


def codex_section() -> str:
    """The AGENTS.md section for Codex, derived from the canonical SKILL.md."""
    return f"{SECTION_START}\n{codex_body_for(_canonical_text())}{SECTION_END}\n"


def install_codex(dest: Path) -> Path:
    """Write the prc-explain section into ``dest/AGENTS.md``. Returns the path."""
    written = dest / "AGENTS.md"
    section = codex_section().strip() + "\n"
    if written.is_file():
        text = written.read_text()
        if SECTION_START in text and SECTION_END in text:
            before, _, rest = text.partition(SECTION_START)
            _, _, after = rest.partition(SECTION_END)
            written.write_text(before + section + after.lstrip("\n"))
        else:
            if not text.endswith("\n"):
                text += "\n"
            written.write_text(text + "\n" + section)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        written.write_text("# Agent notes\n\n" + section)

    return written


def install(agent: str, dest: Path) -> Path:
    """Install the skill for ``agent`` into ``dest``. Returns the path written."""
    if agent == "claude":
        return install_claude(dest)
    if agent == "codex":
        return install_codex(dest)

    raise ValueError(f"unknown agent {agent!r}; choose claude or codex")

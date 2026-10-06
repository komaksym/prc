"""Install the prc-explain board-writer skill for the user's coding agent.

Claude reads skills from ``<dest>/prc-explain/SKILL.md``. Codex reads the
``AGENTS.md`` section this module writes. Both installers print the path
they wrote and never touch the user's real ``~/.claude`` unless the caller
passes it as ``dest`` explicitly.
"""

from __future__ import annotations

from pathlib import Path

SKILL_NAME = "prc-explain"
SECTION_START = "<!-- prc-explain:start -->"
SECTION_END = "<!-- prc-explain:end -->"


def skill_source() -> Path:
    """The SKILL.md shipped inside this package."""
    return Path(__file__).resolve().parent / "SKILL.md"


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
    written.write_text(skill_source().read_text())

    return written


def codex_section() -> str:
    """The AGENTS.md section for Codex: the same 9 steps, condensed."""
    return f"""{SECTION_START}
## prc-explain: PR explainer board writer

You write one JSON file, the board. `prc` turns it into a narrated
1920x1080 video plus a map page, and checks every fact in it. `prc` never
posts anything to GitHub; the files stay local. Describe the pull
request; do not sell it. One idea per scene, sentences under 20 words.

1. Render the deterministic outputs: `prc explain --source <PR URL>`
   (add `--map <stored map.json>` when GitHub is unreachable). It prints
   the `out` folder with `map.json`, the only source of truth below.
2. Run `prc board guide` and follow it: title, groups before/after, one
   diff scene, one evidence scene, outro. 45 to 75 seconds.
3. Pick lines with `prc board show --map map.json` and
   `prc board find --map map.json "needle"`. List refs, never code.
4. Write `board.json`. Every `match` is an exact substring of its line.
   Never type a number on screen; use facts (`{{tests_added}}`) or leave
   `big` out. Titles, subs and notes are unchecked, so keep them true.
   When unsure, say less.
5. Run `prc board check board.json --map map.json` until it passes
   (`<n> receipts verified`); fix each error line and re-run.
6. Run `prc board coverage board.json --map map.json`; say what is left out.
7. Render: `prc explain --source <PR URL> --board board.json`
   (plus `--map` when step 1 needed it).
8. Review frames at 800 px wide (`ffmpeg -ss <t> -i video.mp4 -frames:v 1
   -vf scale=800:-1 f.png`), fix unreadable text, repeat from step 5.
9. Report the out folder (`map.json`, `map.html`, `board.json`,
   `video.mp4`, `run.json`) and say prc posted nothing.
{SECTION_END}
"""


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

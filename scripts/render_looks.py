"""Render finished PRC outputs again in every look, and write one hub page.

Each look re-records the same filled board with the same narration, so the looks differ
only in paper, ink, type and card shape. The infographic is the gated one from the
source output, shared by every look.

    .venv/bin/python scripts/render_looks.py                     # every PR, every look
    .venv/bin/python scripts/render_looks.py --pr linkedin-mdp-5 --look essay --keys-only
    .venv/bin/python scripts/render_looks.py --hub-only
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prc.explainer.page import render_page  # noqa: E402
from prc.explainer.render import render_look  # noqa: E402
from prc.explainer.themes import LOOKS  # noqa: E402

SOURCE = ROOT / "artifacts/output-v5/outputs/final"
OUT = ROOT / "artifacts/v12-looks"
GIT_CACHE = ROOT / "artifacts/output-v4/git-cache"


def sources() -> dict[str, Path]:
    """Short PR slug (repo-number) to its finished output directory."""
    found = {}
    for d in sorted(SOURCE.iterdir()):
        if (d / "board.json").exists():
            owner, rest = d.name.split("-", 1)
            slug = rest.rsplit("-", 1)[0]
            found[slug] = d
    return found


def git_dir(m: dict) -> str | None:
    """The PR's bare clone, so the page highlights whole files like the baseline did."""
    repo, number = str(m["pr"]).split("#")
    found = GIT_CACHE / f"{repo.replace('/', '__')}__{number}.git"
    return str(found) if found.exists() else None


def build(slug: str, src: Path, name: str, keys_only: bool) -> Path:
    out = OUT / slug / name
    out.mkdir(parents=True, exist_ok=True)
    board = json.loads((src / "board.json").read_text())
    m = json.loads((src / "map.json").read_text())
    rendered = render_look(src, out, name, keys_only=keys_only)
    info = src / "infographic.png"
    if info.exists():
        shutil.copyfile(info, out / "infographic.png")
    render_page(
        board,
        m,
        out,
        rendered.duration,
        has_video=not keys_only,
        infographic=info.read_bytes() if info.exists() else None,
        git_dir=git_dir(m),
        look_name=name,
    )
    print(f"{slug} {name}: {rendered.duration:.1f}s -> {out}", flush=True)
    return out


def hub(found: dict[str, Path]) -> Path:
    rows = []
    for slug, src in found.items():
        m = json.loads((src / "map.json").read_text())
        title = html.escape(str(m["title"]))
        cells = []
        for name, lk in LOOKS.items():
            d = OUT / slug / name
            if not (d / "page.html").exists():
                cells.append(
                    f"<td class='none'>{html.escape(lk.label)}<br><small>not built</small></td>"
                )
                continue
            shot = f"{slug}/{name}/keys/02a.png"
            links = [f"<a href='{slug}/{name}/page.html'>Page</a>"]
            if (d / "video.mp4").exists():
                links.append(f"<a href='{slug}/{name}/video.mp4'>Video</a>")
            if (d / "infographic.png").exists():
                links.append(f"<a href='{slug}/{name}/infographic.png'>Infographic</a>")
            cells.append(
                f"<td><a class='thumb' href='{slug}/{name}/page.html'>"
                f"<img src='{shot}' alt='{html.escape(lk.label)} look, scene 2 of {html.escape(slug)}' loading='lazy'></a>"
                f"<b>{html.escape(lk.label)}</b><span>{' · '.join(links)}</span></td>"
            )
        pr = html.escape(str(m["pr"]))
        number = str(m["pr"]).split("#")[1]
        repo = str(m["pr"]).split("#")[0]
        rows.append(
            f"<tr><th scope='row'><a href='https://github.com/{html.escape(repo)}/pull/{number}' target='_blank' rel='noopener'>{pr}</a>"
            f"<p>{title}</p></th>{''.join(cells)}</tr>"
        )
    heads = "".join(f"<th scope='col'>{html.escape(lk.label)}</th>" for lk in LOOKS.values())
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>PRC looks: full artifacts</title>
<style>
body{{margin:0;background:#f7f6f2;color:#1d1c1a;font:15px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:1720px;margin:0 auto;padding:32px 28px 64px}}
h1{{font:600 26px/1.2 system-ui;margin:0 0 6px}} .lead{{color:#5d5a53;margin:0 0 24px;max-width:80ch}}
table{{border-collapse:separate;border-spacing:12px 12px;width:100%;table-layout:fixed}}
thead th{{text-align:left;font:600 13px system-ui;letter-spacing:.08em;text-transform:uppercase;color:#6b675e}}
tbody th{{text-align:left;vertical-align:top;width:200px;font:600 15px system-ui}} tbody th p{{font-weight:400;color:#5d5a53;margin:6px 0 0;font-size:14px}}
td{{vertical-align:top;background:#fff;border:1px solid #e4e1d8;border-radius:10px;padding:10px}}
td.none{{color:#8a857a}}
td img{{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:6px;border:1px solid #e4e1d8;margin-bottom:8px}}
td b{{display:block;font-size:14px}} td span{{font-size:14px}}
a{{color:#1f5fbf}} a:hover{{text-decoration-thickness:2px}}
</style></head><body><main>
<h1>PRC artifacts for three pull requests, in five looks</h1>
<p class='lead'>Each row is one pull request. Each column is one look. Every look uses the same storyboard, narration and timing, so only paper, ink, type and card shape change. The first column is the original dark baseline. Each infographic is the gated infographic from the baseline output, shared by every look. Open a page to step through it, or open the video to watch it.</p>
<table><thead><tr><th scope='col'>Pull request</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table>
</main></body></html>"""
    path = OUT / "index.html"
    path.write_text(page)
    print(f"hub -> {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", action="append", help="slug, for example linkedin-mdp-5")
    parser.add_argument("--look", action="append", choices=list(LOOKS))
    parser.add_argument("--keys-only", action="store_true", help="key frames and page, no video")
    parser.add_argument("--hub-only", action="store_true")
    args = parser.parse_args()
    found = sources()
    if not args.hub_only:
        for slug in args.pr or list(found):
            for name in args.look or list(LOOKS):
                build(slug, found[slug], name, args.keys_only)
    hub(found)


if __name__ == "__main__":
    main()

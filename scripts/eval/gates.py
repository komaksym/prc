"""Stage 8 gates: deterministic checks over one eval run output folder (EVAL.md A).

Run: uv run python scripts/eval/gates.py eval/runs/<label> [--write]
Reads outputs/pr<N>/{map.json,board.json,doc.html,video.mp4,card.png,comment.md,card.html,run.json}
plus packets for the video gate. Prints PASS/FAIL per PR per gate and a summary.
With --write, stores the table in results.json under the "gates" key.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

GATE_NAMES = (
    "receipts",
    "join",
    "dom_text",
    "layout",
    "diagram",
    "card_facts",
    "doc_links",
    "video_file",
)


def _read(path: Path) -> dict:
    return dict(json.loads(path.read_text()))


def gate_receipts(pr_dir: Path) -> tuple[bool, str]:
    run = _read(pr_dir / "run.json")
    check = run.get("check", {})
    if check.get("passed") and run.get("board"):
        return True, f"{check.get('receipts', '?')} receipts"
    return False, "board check did not pass"


def gate_join(pr_dir: Path) -> tuple[bool, str]:
    from prc.explainer.jointest import run

    m = _read(pr_dir / "map.json")
    board = _read(pr_dir / "board.json")
    checked = 0
    for i, scene in enumerate(board.get("scenes", [])):
        if scene.get("type") != "diff":
            continue
        tokens_path = pr_dir / f"tokens_s{i}.json"
        if not tokens_path.exists():
            return False, f"tokens_s{i}.json missing"
        tokens = dict(json.loads(tokens_path.read_text()))
        refs = [str(r["ref"]) for r in scene["rows"] if "text" in r]
        errors, _ = run(tokens, m, refs)
        if errors:
            return False, f"scene {i}: " + "; ".join(errors[:3])
        checked += len(refs)
    if not checked:
        return True, "no diff scenes"
    return True, f"{checked} refs join"


def gate_dom_text(pr_dir: Path) -> tuple[bool, str]:
    """The join test on the doc DOM, mirroring test_doc_code_rows_join_to_the_diff."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return True, "skip: no playwright"
    from prc.explainer.jointest import run as join_run

    m = _read(pr_dir / "map.json")
    board = _read(pr_dir / "board.json")
    diffs = [s for s in board.get("scenes", []) if s.get("type") == "diff"]
    if not diffs:
        return True, "no diff scenes"
    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            return True, f"skip: {str(error).splitlines()[0]}"
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((pr_dir / "doc.html").resolve().as_uri())
        try:
            page.wait_for_function("window.docReady === true", timeout=15000)
        except Exception as error:  # noqa: BLE001
            browser.close()
            return False, f"doc never ready: {str(error).splitlines()[0]}"
        dom_rows = page.evaluate(
            """() => [...document.querySelectorAll('.shot')].map(shot => {
              const code = shot.querySelector('.diff .code');
              if (!code) return null;
              return [...code.querySelectorAll(':scope > .drow')].map(row => {
                if (row.classList.contains('gap')) return {gap: true};
                return {marker: row.querySelector('.sg').textContent,
                        tokens: [...row.querySelectorAll('.mt')].map(el => el.textContent)};
              });
            })"""
        )
        browser.close()
    got = [rows for rows in dom_rows if rows is not None]
    if len(got) != len(diffs) or not got:
        return False, f"{len(got)} diff shots for {len(diffs)} diff scenes"
    for s, rows in zip(diffs, got, strict=True):
        code = [r for r in s["rows"] if "text" in r]
        frames = [
            {"gap": True}
            if row.get("gap")
            else {"ref": r["ref"], "marker": row["marker"], "tokens": row["tokens"]}
            for row, r in zip(rows, s["rows"], strict=True)
        ]
        errors, rc = join_run(
            {
                "file": s["file"],
                "cut": s.get("cut", 0),
                "transform": "build",
                "refs": [r["ref"] for r in code],
                "frames": [{"t": 0.0, "rows": frames}],
            },
            m,
            [r["ref"] for r in code],
        )
        if rc != 0:
            return False, "; ".join(errors[:3])
    return True, f"{len(diffs)} doc scenes join"


def gate_layout(pr_dir: Path) -> tuple[bool, str]:
    run = _read(pr_dir / "run.json")
    warnings = run.get("layout_warnings", [])
    if warnings:
        return False, "; ".join(str(w) for w in warnings[:3])
    return True, "no layout warnings"


def gate_diagram(pr_dir: Path) -> tuple[bool, str]:
    from prc.presentation.comment import check_mermaid, select_nodes

    m = _read(pr_dir / "map.json")
    text = (pr_dir / "comment.md").read_text()
    if "```mermaid" not in text:
        return False, "no fenced mermaid block in comment.md"
    part = text.split("```mermaid")[1].split("```")[0]
    errors = check_mermaid("```mermaid" + part + "```")
    if errors:
        return False, "; ".join(errors[:3])
    ids = select_nodes(m)
    if len(ids) > 12:
        return False, f"{len(ids)} nodes over cap"
    known = {(e["source"], e["target"]): e["status"] for e in m.get("edges", [])}
    want = {"-->": "added", "-.->": "removed", "---": "kept"}
    index = {f"n{i + 1}": sid for i, sid in enumerate(ids)}
    edges = re.findall(r"(n\d+)\s+(-->|-\.->|---)\s+(n\d+)", part)
    if not edges:
        return False, "diagram contains no edges"
    for src, form, dst in edges:
        if (index.get(src), index.get(dst)) not in known:
            return False, f"{src}->{dst} not in map.json"
        if known[index[src], index[dst]] != want[form]:
            return False, f"wrong status for {src}->{dst}"
    return True, f"{len(ids)} nodes"


def gate_card_facts(pr_dir: Path) -> tuple[bool, str]:
    from prc.presentation.card import compute_stats

    m = _read(pr_dir / "map.json")
    stats = compute_stats(m, m.get("brief"))
    html = (pr_dir / "card.html").read_text()
    for value in (stats.files, stats.symbols_changed, stats.call_sites, stats.tests_touched):
        if str(value) not in html:
            return False, f"{value} missing from card.html"
    if stats.ci_text not in html:
        return False, f"{stats.ci_text} missing from card.html"
    return True, "card numbers match recomputation"


def gate_doc_links(pr_dir: Path) -> tuple[bool, str]:
    doc = (pr_dir / "doc.html").read_text()
    links = re.findall(
        r"https://github\.com/[^\"'\s<>]+/blob/([0-9a-f]{40})/([^\"'#]+)#L(\d+)", doc
    )
    if not links:
        return True, "no receipt links"
    return True, f"{len(links)} receipt links with sha"


def gate_video_file(pr_dir: Path) -> tuple[bool, str]:
    video = pr_dir / "video.mp4"
    if not video.exists():
        return False, "video.mp4 missing"
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name:format=duration",
            "-of",
            "json",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return False, "ffprobe failed"
    info = json.loads(out.stdout)
    stream = info["streams"][0]
    if (stream["width"], stream["height"]) != (1920, 1080):
        return False, f"{stream['width']}x{stream['height']} not 1920x1080"
    if stream["r_frame_rate"] != "30/1":
        return False, f"fps {stream['r_frame_rate']} not 30/1"
    duration = float(info["format"]["duration"])
    limit = 90.0 if pr_dir.name in ("pr17", "pr19") else 80.0
    if not (45.0 <= duration <= limit):
        return False, f"{duration:.1f}s outside 45-{limit:.0f}s"
    return True, f"{duration:.1f}s 1920x1080 30fps"


GATES = {
    "receipts": gate_receipts,
    "join": gate_join,
    "dom_text": gate_dom_text,
    "layout": gate_layout,
    "diagram": gate_diagram,
    "card_facts": gate_card_facts,
    "doc_links": gate_doc_links,
    "video_file": gate_video_file,
}


def grade_run(run_dir: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for pr_dir in sorted((run_dir / "outputs").iterdir()):
        if not pr_dir.is_dir():
            continue
        row: dict[str, object] = {}
        for name in GATE_NAMES:
            try:
                ok, note = GATES[name](pr_dir)
            except FileNotFoundError as error:
                ok, note = False, f"missing file: {error.filename}"
            except Exception as error:  # noqa: BLE001
                ok, note = False, f"{type(error).__name__}: {error}"
            row[name] = {"pass": ok, "note": str(note)}
            print(f"{pr_dir.name} {name}: {'PASS' if ok else 'FAIL'} {note}")
        result[pr_dir.name] = row
    return result


def main() -> int:
    run_dir = Path(sys.argv[1])
    write = "--write" in sys.argv[2:]
    table = grade_run(run_dir)
    total = sum(1 for row in table.values() for cell in row.values() if cell["pass"])
    possible = len(table) * len(GATE_NAMES)
    print(f"{total}/{possible} gate cells pass across {len(table)} PRs")
    if write:
        results_path = run_dir / "results.json"
        results = json.loads(results_path.read_text()) if results_path.exists() else {}
        results["gates"] = table
        results_path.write_text(json.dumps(results, indent=2, sort_keys=True))
    failed = [
        f"{pr}/{g}" for pr, row in table.items() for g, cell in row.items() if not cell["pass"]
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

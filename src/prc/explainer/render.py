"""Frame-by-frame render of a checked board: Chromium seeks, ffmpeg encodes. Never realtime."""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prc.explainer import highlight
from prc.explainer.check import verify_board
from prc.explainer.diffrows import pair_rows, wrap_row
from prc.explainer.jointest import run as join_run
from prc.explainer.timing import fit_sentences
from prc.explainer.voice import Backend

ASSETS = Path(__file__).resolve().parent / "assets"
FPS = 30

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body class="video"><div id="app" class="emount"><div class="escale" id="scale"></div></div>
<script>window.BOARD = {board};</script><script>{js}
prcMount(document.getElementById('scale'), window.BOARD, null);</script></body></html>"""


class RenderError(RuntimeError):
    """A missing tool or a failed render, worded for the person running the CLI."""


@dataclass(frozen=True)
class Rendered:
    duration: float
    frames: int
    layout_warnings: list[str]
    log: list[dict[str, Any]]


def check_tools() -> None:
    if not shutil.which("ffmpeg"):
        raise RenderError("ffmpeg is not on PATH. Install it (for example `brew install ffmpeg`).")
    if not shutil.which("ffprobe"):
        raise RenderError("ffprobe is not on PATH. Install it (for example `brew install ffmpeg`).")
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as error:
        raise RenderError(
            "Playwright is not installed. Run `uv sync --extra video` (or "
            "`pip install 'prc[video]'`), then `playwright install chromium`."
        ) from error


def layout(scene: dict[str, Any], m: dict[str, Any]) -> None:
    sym = {s["id"]: s for s in m["symbols"]}
    known = {(e["source"], e["target"]): e["status"] for e in m["edges"]}
    edges = []

    for e in scene["edges"]:
        src, dst = (e[0], e[1]) if isinstance(e, list) else (e["s"], e["t"])
        edges.append(
            {
                "s": src,
                "t": dst,
                "status": known.get((src, dst), e["status"] if isinstance(e, dict) else "kept"),
            }
        )

    depth = {i: 0 for i in scene["nodes"]}
    for _ in scene["nodes"]:
        for e in edges:
            depth[e["t"]] = max(depth[e["t"]], depth[e["s"]] + 1)

    columns: dict[int, list[str]] = {}
    for i in scene["nodes"]:
        columns.setdefault(depth[i], []).append(i)

    nodes, x, h, gap_x, gap_y = [], 0.0, 92, 150, 34
    for d in sorted(columns):
        col = columns[d]
        widths = [max(len(sym[i]["qualname"]) * 18.1, len(sym[i]["path"]) * 10.9) + 64 for i in col]
        span = len(col) * h + (len(col) - 1) * gap_y
        for k, (i, w) in enumerate(zip(col, widths, strict=True)):
            nodes.append(
                {
                    "id": i,
                    "label": sym[i]["qualname"],
                    "sub": sym[i]["path"],
                    "status": sym[i]["status"],
                    "x": x + (max(widths) - w) / 2,
                    "y": -span / 2 + k * (h + gap_y),
                    "w": w,
                    "h": h,
                }
            )
        x += max(widths) + gap_x

    scene["nodes"], scene["edges"] = nodes, edges


def fill(
    board: dict[str, Any],
    m: dict[str, Any],
    facts: dict[str, Any],
    git_dir: str | None = None,
) -> None:
    repo, number = m["pr"].split("/")[1].split("#")
    added = sum(f["added"] for f in m["brief"]["files"])
    removed = sum(f["removed"] for f in m["brief"]["files"])
    board["header"] = f"<b>{repo} #{number}</b> · {m['author']}"
    values = {k: v for k, v in facts.items() if isinstance(v, int)}

    for i, s in enumerate(board["scenes"]):
        s["i"] = i
        cites = [
            re.sub(r":-(\d+)$", r":\1 (old)", c["line"].rsplit("/", 1)[-1])
            for c in s.get("cite", [])
        ]
        s["footer"] = ("receipts   " + "  ·  ".join(cites[:4])) if cites else ""

        if s["type"] == "title":
            s["title"] = m["title"]
            s["meta"] = (
                f'<span class="add">+{added}</span> <span class="del">−{removed}</span>'
                f" · {len(m['brief']['files'])} files · {m['pr']}"
            )
            s["footer"] = f"base {m['base_sha'][:7]}  →  head {m['head_sha'][:7]}"
            segments, rest = [], m["title"]
            for claim in s.get("claims", []):
                before, _, rest = rest.partition(claim["text"])
                segments += [{"text": before}, {"text": claim["text"], "claim": claim["n"]}]
            if s.get("claims"):
                s["segments"] = segments + [{"text": rest}]
        if s["type"] == "list":
            if "more" not in s:
                rest = facts["tests_added"] - len(s["items"])
                s["more"] = (
                    f"+ {rest} more" if s.get("big") == "{tests_added}" and rest > 0 else None
                )
            s["big"] = s.get("big", "").format(**values)
        if s["type"] == "receipt":
            s["verdict"] = facts["verdicts"][i]
            s["footer"] = ""
        if s["type"] == "stats":
            for c in s["cards"]:
                c["value"] = c["value"].format(**values)
        if s["type"] == "outro":
            s["url"] = (m.get("url") or "pr").removeprefix("https://")
        if s["type"] == "diff":
            code = [r for r in s["rows"] if "text" in r]
            for r in code:
                r["text"] = r["text"].expandtabs(4).rstrip()
            cut = min(
                (len(r["text"]) - len(r["text"].lstrip()) for r in code if r["text"].strip()),
                default=0,
            )
            for r in code:
                r["text"] = r["text"][cut:]
            s["cut"] = cut
            nums = [r["num"] for r in code]
            s["gutter"] = math.ceil((len(str(max(nums))) + 1) * 0.72) if nums else 1
            fe = next((f for f in m["files"] if f["path"] == s["file"]), None)
            highlight.attach_tokens(
                s["rows"],
                s["file"],
                cut,
                git_dir,
                m["head_sha"],
                m["base_sha"],
                fe["hunks"] if fe else [],
            )
            pair_rows(s["rows"])
            for r in s["rows"]:
                if "text" not in r:
                    continue
                hang, breaks = wrap_row(r["tokens"], 72 - s["gutter"])
                r["hang"], r["breaks"] = hang, breaks
            s["lang"] = {
                ".py": "py",
                ".ts": "js",
                ".tsx": "js",
                ".js": "js",
                ".jsx": "js",
                ".mjs": "js",
            }.get(Path(s["file"]).suffix, "")
            s["footer"] = (
                f"receipts   {len(code)} lines quoted verbatim from the diff of {s['file'].rsplit('/', 1)[-1]}"
            )


def join_gate(board: dict[str, Any], m: dict[str, Any], out: Path) -> None:
    """Write tokens_s<i>.json per diff scene and run the join test. Stops the build on failure."""
    for i, s in enumerate(board["scenes"]):
        if s["type"] != "diff":
            continue
        code = [r for r in s["rows"] if "text" in r]
        doc = {
            "scene": i,
            "file": s["file"],
            "cut": s["cut"],
            "transform": "build",
            "refs": [r["ref"] for r in code],
            "frames": [
                {
                    "t": None,
                    "rows": [
                        {"gap": True}
                        if "text" not in r
                        else {
                            "ref": r["ref"],
                            "marker": "+" if r["op"] == "+" else "−" if r["op"] == "-" else "",
                            "tokens": r["tokens"],
                        }
                        for r in s["rows"]
                    ],
                }
            ],
        }
        (out / f"tokens_s{i}.json").write_text(json.dumps(doc))
        errs, rc = join_run(doc, m, [str(r["ref"]) for r in code])
        if rc != 0:
            raise RenderError(f"join gate failed for diff scene {i}:\n" + "\n".join(errs))


def board_json(board: dict[str, Any]) -> str:
    """Board JSON safe to inline in a <script> block: </script> never appears mid-string."""
    return json.dumps(board).replace("</", "<\\/")


def mix_narration(clips: list[tuple[float, Path]], cursor: float, out: Path) -> None:
    inputs, chains = [], []
    for n, (t, wav) in enumerate(clips):
        inputs += ["-i", str(wav)]
        chains.append(f"[{n}:a]adelay={int(round(t * 1000))}:all=1[a{n}]")
    mix = "".join(f"[a{n}]" for n in range(len(clips)))
    mix += (
        f"amix=inputs={len(clips)}:normalize=0:dropout_transition=0,apad,atrim=0:{cursor:.3f}[out]"
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains + [mix]),
         "-map", "[out]", "-ar", "48000", "-ac", "1", str(out)],
        check=True,
    )  # fmt: skip


def silence(cursor: float, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-t", f"{cursor:.3f}", "-ar", "48000", "-ac", "1", str(out)],
        check=True,
    )  # fmt: skip


def render(
    board: dict[str, Any],
    m: dict[str, Any],
    facts: dict[str, Any],
    out: Path,
    backend: Backend,
    git_dir: str | None = None,
    keys_only: bool = False,
) -> Rendered:
    check_tools()
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    (out / "audio").mkdir(exist_ok=True)
    fill(board, m, facts, git_dir)
    join_gate(board, m, out)
    log: list[dict[str, Any]] = []
    cursor, clips = fit_sentences(board, backend, out / "audio", log)
    for s in board["scenes"]:
        if s["type"] == "graph":
            layout(s, m)
    if log:
        (out / "phrases.json").write_text(json.dumps(log, indent=1))

    narration = out / "narration.wav"
    if backend.has_audio:
        mix_narration(clips, cursor, narration)
    else:
        silence(cursor, narration)

    player = out / "player.html"
    player.write_text(
        PAGE.format(
            css=(ASSETS / "engine.css").read_text(),
            board=board_json(board),
            js=(ASSETS / "engine.js").read_text(),
        )
    )

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as error:  # noqa: BLE001
            raise RenderError(
                f"Chromium cannot launch ({str(error).splitlines()[0]}). "
                "Run `playwright install chromium`."
            ) from error
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(player.as_uri())
        page.wait_for_function("window.ready === true", timeout=15000)
        if errors:
            browser.close()
            raise RenderError("page errors: " + " | ".join(errors))
        diffs = [
            {
                "i": s["i"],
                "refs": [r["ref"] for r in s["rows"] if "text" in r],
                "texts": [r["text"] for r in s["rows"] if "text" in r],
            }
            for s in board["scenes"]
            if s["type"] == "diff"
        ]
        dom_errs = page.evaluate(
            """(diffs) => {
          const errs = [];
          const boxes = [...document.querySelectorAll('.diff .code')];
          if (boxes.length !== diffs.length) return [`${boxes.length} code boxes, expected ${diffs.length}`];
          boxes.forEach((box, i) => {
            const cts = [...box.querySelectorAll('.drow .ct')];
            const exp = diffs[i];
            if (cts.length !== exp.texts.length) { errs.push(`scene ${exp.i}: ${cts.length} .ct rows, expected ${exp.texts.length}`); return; }
            cts.forEach((ct, k) => { if (ct.textContent !== exp.texts[k]) errs.push(`scene ${exp.i} row ${exp.refs[k]}: DOM ${JSON.stringify(ct.textContent)} != ${JSON.stringify(exp.texts[k])}`); });
          });
          return errs;
        }""",
            diffs,
        )
        if dom_errs:
            browser.close()
            raise RenderError("DOM text mismatch:\n  " + "\n  ".join(dom_errs))
        warnings = list(page.evaluate("window.lint || []"))

        keys = out / "keys"
        keys.mkdir(exist_ok=True)
        for s in board["scenes"]:
            for tag, tt in (("a", (s["start"] + s["end"]) / 2), ("b", s["end"] - 0.45)):
                page.evaluate(f"seek({tt})")
                page.screenshot(path=str(keys / f"{s['i']:02d}{tag}.png"))

        if not keys_only:
            mp4 = out / "video.mp4"
            ffmpeg = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS),
                 "-c:v", "mjpeg", "-i", "-", "-i", str(narration),
                 "-vf", "scale=out_range=tv,format=yuv420p",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "160k",
                 "-shortest", "-movflags", "+faststart", str(mp4)],
                stdin=subprocess.PIPE,
            )  # fmt: skip
            assert ffmpeg.stdin is not None
            for n in range(int(round(cursor * FPS)) + 1):
                page.evaluate(f"seek({n / FPS})")
                ffmpeg.stdin.write(page.screenshot(type="jpeg", quality=92))
            ffmpeg.stdin.close()
            if ffmpeg.wait() != 0:
                browser.close()
                raise RenderError("ffmpeg failed while encoding video.mp4")

        if errors:
            browser.close()
            raise RenderError("page errors: " + " | ".join(errors))
        browser.close()

    return Rendered(cursor, int(round(cursor * FPS)) + 1, warnings, log)


def render_board(
    board_path: Path, map_path: Path, out: Path, backend: Backend, git_dir: str | None = None
) -> Rendered:
    """Check, fill and render a board file against a map file. Used by tests and the CLI."""
    board = json.loads(board_path.read_text())
    m = json.loads(map_path.read_text())
    facts = verify_board(board, m)
    return render(board, m, facts, out, backend, git_dir)

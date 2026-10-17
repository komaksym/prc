"""Shoot and record round-7 arena candidates. Throwaway prototype tooling.

python build.py shots [dir ...]   full-page screenshots at 1440 and 800 px, plus page errors
python build.py clips [dir ...]   1280x720 clip per dir via ?clip=1, poster and contact sheet
A dir is relative to artifacts/v7-arena, for example candidate-1/wondering.
"""
import functools, http.server, json, pathlib, subprocess, sys, threading, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "_out"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def dirs(names):
    return names or sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.glob("*/*/index.html"))


def slug(d):
    return d.replace("/", "--")


def shots(names):
    OUT.mkdir(exist_ok=True)
    srv, base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for d in dirs(names):
            rep = {}
            for w in (1440, 800):
                ctx = b.new_context(viewport={"width": w, "height": 900})
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.goto(base + "/" + d + "/index.html", wait_until="networkidle")
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(800)
                out = OUT / ("%s-%d.png" % (slug(d), w))
                pg.screenshot(path=str(out), full_page=True)
                rep[w] = {"shot": str(out), "errors": errs, "height": pg.evaluate("document.documentElement.scrollHeight")}
                ctx.close()
            print(json.dumps({d: rep}), flush=True)
        b.close()
    srv.shutdown()


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def clips(names):
    raw_dir = OUT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    srv, base = serve()
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for d in dirs(names):
            ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(raw_dir), record_video_size={"width": 1280, "height": 720})
            t0 = time.monotonic()
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            try:
                pg.goto(base + "/" + d + "/index.html?clip=1")
                pg.wait_for_function("window.__ready === true", timeout=20000)
                pg.wait_for_timeout(300)
                t_go = time.monotonic() - t0
                pg.evaluate("window.startClip()")
                pg.wait_for_function("window.__clipDone === true", timeout=90000)
                marks = pg.evaluate("window.__marks")
            except Exception as e:
                report[d] = {"error": str(e)[:300], "page_errors": errs}
                ctx.close()
                print(json.dumps({d: report[d]}), flush=True)
                continue
            dur = time.monotonic() - t0 - t_go
            raw = pg.video.path()
            ctx.close()
            out = ROOT / d / "clip.webm"
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % max(0, t_go - 0.05), "-i", raw, "-t", "%.2f" % dur,
                 "-c:v", "libvpx-vp9", "-b:v", "1600k", "-deadline", "good", "-cpu-used", "4", "-row-mt", "1", "-an", str(out)])
            pathlib.Path(raw).unlink()
            length = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]).stdout.strip())
            poster_t = round(max(0.5, (marks[0] if marks else 2) - 0.4), 2)
            poster = ROOT / d / "clip-poster.jpg"
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(poster_t), "-i", str(out), "-frames:v", "1", "-q:v", "3", str(poster)])
            sheet = OUT / ("clip-%s-sheet.png" % slug(d))
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf", "fps=%.4f,scale=640:-1,tile=3x3" % (9 / length), "-frames:v", "1", str(sheet)])
            report[d] = {"clip": str(out), "seconds": round(length, 2), "marks": marks, "sheet": str(sheet), "page_errors": errs}
            print(json.dumps({d: report[d]}), flush=True)
        b.close()
    srv.shutdown()
    (OUT / "clips.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    cmd, names = sys.argv[1], sys.argv[2:]
    {"shots": lambda: shots(names), "clips": lambda: clips(names)}[cmd]()

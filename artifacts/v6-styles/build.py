"""Shoot, record and check the v6 style picker. Throwaway prototype tooling.

python build.py shots [variant ...]      full-page screenshots at 800 and 1440 px
python build.py states                   screenshots of stepper states (B, C)
python build.py clips [variant ...]      record 1280x720 clips, trim, poster, black check, contact sheet
"""
import functools, http.server, json, pathlib, subprocess, sys, threading, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
SHOTS, CLIPS = ROOT / "shots", ROOT / "clips"
VARIANTS = ["control", "a", "b", "c"]
CLIP_URL = {"control-" + p: "control&pal=" + p for p in ("paper", "coded", "marker", "card", "grid", "docs", "cream", "gallery", "cotton", "stone", "ivory", "audun", "belvedir", "omanta", "speko", "gumloop", "bond", "herdr")}  # clip name -> ?clip= query


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def shots(names):
    SHOTS.mkdir(exist_ok=True)
    srv, base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in (1440, 800):
            ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "/picker.html")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(900)
            for v in names:
                pg.keyboard.press(str(VARIANTS.index(v) + 1))
                pg.wait_for_timeout(700)
                out = SHOTS / ("%s-%d.png" % (v, w))
                pg.screenshot(path=str(out), full_page=True)
                print("shot", out, flush=True)
            if errs:
                print("PAGE ERRORS", errs)
            ctx.close()
        b.close()
    srv.shutdown()


def states():
    SHOTS.mkdir(exist_ok=True)
    srv, base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.goto(base + "/picker.html#b")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(800)
        fig = pg.locator("#bDoc")
        for scen in ["complete", "sharing", "supabase_timeout"]:
            pg.click('#bDoc .b-scen button[data-scen="%s"]' % scen)
            for n in range(1, 6):
                pg.click('#bDoc .b-dots button[data-n="%d"]' % n)
                pg.wait_for_timeout(1100)
                if scen != "complete" and n not in (3, 5):
                    continue
                fig.screenshot(path=str(SHOTS / ("state-b-doc-%s-%d.png" % (scen, n))))
        for n in range(1, 4):
            pg.click('#bCode .b-dots button[data-n="%d"]' % n)
            pg.wait_for_timeout(700)
            pg.locator("#bCodeChap .b-scrolly").screenshot(path=str(SHOTS / ("state-b-code-%d.png" % n)))
        pg.goto(base + "/picker.html#c")
        pg.wait_for_timeout(800)
        for ed in ["cDoc", "cRun"]:
            for i in range(5):
                pg.click("#%s .c-steps button[data-i=\"%d\"]" % (ed, i))
                pg.wait_for_timeout(900)
                pg.locator("#" + ed).screenshot(path=str(SHOTS / ("state-c-%s-%d.png" % (ed, i))))
        pg.goto(base + "/picker.html#a")
        pg.wait_for_timeout(800)
        pg.click('.a-play[data-stage="aDoc"]')
        for t in (1500, 3200, 4600):
            pg.wait_for_timeout(t - (0 if t == 1500 else (1500 if t == 3200 else 3200)))
            pg.locator("#aDoc").screenshot(path=str(SHOTS / ("state-a-doc-%d.png" % t)))
        ctx.close()
        b.close()
    srv.shutdown()
    print("states done")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def clips(names):
    CLIPS.mkdir(exist_ok=True)
    raw_dir = CLIPS / "raw"
    raw_dir.mkdir(exist_ok=True)
    srv, base = serve()
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for v in names:
            ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(raw_dir), record_video_size={"width": 1280, "height": 720})
            t0 = time.monotonic()
            pg = ctx.new_page()
            pg.goto(base + "/picker.html?clip=" + CLIP_URL.get(v, v))
            pg.wait_for_function("window.__ready === true", timeout=20000)
            pg.wait_for_timeout(300)
            t_go = time.monotonic() - t0
            pg.evaluate("window.startClip()")
            pg.wait_for_function("window.__clipDone === true", timeout=60000)
            marks = pg.evaluate("window.__marks")
            dur = time.monotonic() - t0 - t_go
            raw = pg.video.path()
            ctx.close()
            out = CLIPS / (v + ".webm")
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % max(0, t_go - 0.05), "-i", raw, "-t", "%.2f" % dur,
                 "-c:v", "libvpx-vp9", "-b:v", "1600k", "-deadline", "good", "-cpu-used", "4", "-row-mt", "1", "-an", str(out)])
            pathlib.Path(raw).unlink()
            length = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]).stdout.strip())
            poster_t = round(max(0.5, marks[0] - 0.4), 2)  # end of moment 1, before the cross-fade
            poster = CLIPS / (v + "-poster.jpg")
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(poster_t), "-i", str(out), "-frames:v", "1", "-q:v", "3", str(poster)])
            stats = run(["ffmpeg", "-loglevel", "error", "-i", str(out), "-vf", "fps=2,signalstats,metadata=print:file=-", "-f", "null", "-"]).stdout
            ymax = [float(l.split("=")[1]) for l in stats.splitlines() if "lavfi.signalstats.YMAX=" in l]
            yavg = [float(l.split("=")[1]) for l in stats.splitlines() if "lavfi.signalstats.YAVG=" in l]
            black = [i / 2 for i, y in enumerate(ymax) if y < 60]
            sheet = SHOTS / ("clip-%s-sheet.png" % v)
            SHOTS.mkdir(exist_ok=True)
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf", "fps=%.4f,scale=640:-1,tile=3x3" % (9 / length), "-frames:v", "1", str(sheet)])
            report[v] = {"clip": str(out), "seconds": round(length, 2), "poster": str(poster), "poster_at": poster_t, "moment_marks": marks, "frames_sampled": len(ymax),
                         "min_ymax": min(ymax), "min_yavg": round(min(yavg), 1), "black_frames_at": black, "sheet": str(sheet)}
            print(json.dumps(report[v]), flush=True)
        b.close()
    srv.shutdown()
    rep = CLIPS / "report.json"
    old = json.loads(rep.read_text()) if rep.exists() else {}
    old.update(report)
    rep.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    cmd, names = sys.argv[1], sys.argv[2:] or VARIANTS
    {"shots": lambda: shots(names), "states": states, "clips": lambda: clips(names)}[cmd]()


#!/usr/bin/env python3
"""Supervised handoff for the paired session hub.

Start or reuse one supervised hub process for a given study directory,
detached from the agent session so it survives after the turn ends
(detached via start_new_session, which calls setsid; equivalent to a
background nohup pidfile launch). Wait until the exact printed URL answers
from the host. Load that exact URL in real Chromium and require the hub to
render. Drive one read-only interaction (Prepare next reading -> preview)
that must not mutate the study. Hold a silent preconnect socket open during
the check and require the hub to keep answering afterwards. Write a handoff
record under artifacts/handoff/ with url, port, pid, pidfile, screenshot,
and each check result. Refuse to print a URL when any check fails:
on failure this script exits nonzero with HANDOFF REFUSED on stderr and
prints no URL to stdout.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD_DIR = ROOT / "artifacts" / "handoff"
DEFAULT_PIDFILE = DEFAULT_RECORD_DIR / "study-hub.pid"
DEFAULT_BROWSER_CACHE = Path("/Users/koval/dev/prc/artifacts/release/browser-cache")
FORBIDDEN_SUBSTR = "paired-study/private"
PREPARE_LABEL = "Prepare next reading"


def _die(message: str, code: int = 1) -> None:
    print(f"handoff_study_hub: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _refuse(message: str) -> None:
    # Never print a URL on this path. Stdout stays empty so a caller
    # cannot copy a dead hub address. Details go to stderr only.
    print(f"HANDOFF REFUSED: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pidfile(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "pid" in data:
            return data
    except ValueError:
        pass
    try:
        return {"pid": int(raw.split()[0])}
    except ValueError:
        return None


def _write_pidfile(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as err:
        try:
            body = err.read()
        except Exception:
            body = b""
        return int(err.code), body


def _wait_for_url(url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, _ = _http_get(url + "/api/state", timeout=3.0)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _session_hash(study: Path) -> str:
    data = (study / "session.json").read_bytes()
    return hashlib.sha256(data).hexdigest()


def _stop_pidfile(pidfile: Path) -> int:
    data = _read_pidfile(pidfile)
    if not data:
        print(f"no supervised hub at {pidfile}", flush=True)
        return 0
    pid = int(data["pid"])
    if not _is_alive(pid):
        pidfile.unlink(missing_ok=True)
        print(f"hub pid {pid} already exited; cleared {pidfile}", flush=True)
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as err:
        _die(f"cannot signal pid {pid}: {err}")
    for _ in range(20):
        if not _is_alive(pid):
            break
        time.sleep(0.25)
    else:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
    pidfile.unlink(missing_ok=True)
    print(f"stopped supervised hub pid {pid}; cleared {pidfile}", flush=True)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Supervise one study hub, prove the exact URL in Chromium, record the handoff."
    )
    parser.add_argument(
        "study", type=Path, help="study directory to serve (a copy, never the sealed original)"
    )
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 picks a free port")
    parser.add_argument("--pidfile", type=Path, default=DEFAULT_PIDFILE)
    parser.add_argument("--record-dir", type=Path, default=DEFAULT_RECORD_DIR)
    parser.add_argument(
        "--timeout", type=float, default=20.0, help="seconds to wait for the URL to answer"
    )
    parser.add_argument(
        "--stop", action="store_true", help="stop the supervised hub named by --pidfile"
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    pidfile = Path(args.pidfile)
    if not pidfile.is_absolute():
        pidfile = (ROOT / pidfile).resolve()
    record_dir = Path(args.record_dir)
    if not record_dir.is_absolute():
        record_dir = (ROOT / record_dir).resolve()
    record_dir.mkdir(parents=True, exist_ok=True)

    if args.stop:
        return _stop_pidfile(pidfile)

    study = Path(args.study).resolve()
    if FORBIDDEN_SUBSTR in str(study):
        _die(
            f"refusing sealed original under {FORBIDDEN_SUBSTR}; "
            "copy the study outside artifacts/paired-study/private first "
            "(the live operator server must stay untouched)"
        )
    if not study.is_dir():
        _die(f"study directory is missing: {study}")
    for name in ("study.json", "session.json"):
        if not (study / name).is_file():
            _die(f"study directory lacks {name}: {study}")

    # Reuse one supervised hub process for this study directory.
    pid: int | None = None
    port: int = int(args.port)
    url: str | None = None
    log_path: Path | None = None
    stored = _read_pidfile(pidfile)
    if stored is not None:
        try:
            old_pid = int(stored["pid"])
        except (KeyError, ValueError, TypeError):
            old_pid = -1
        old_study = stored.get("study")
        old_url = stored.get("url")
        old_port = stored.get("port")
        if old_pid > 0 and _is_alive(old_pid) and old_study == str(study) and old_url:
            if _wait_for_url(str(old_url), timeout=5.0):
                pid, url = old_pid, str(old_url)
                port = int(old_port or 0)
                log_text = stored.get("log")
                log_path = Path(log_text) if log_text else record_dir / f"server-{port}.log"
                print(f"reusing supervised hub pid {pid} at {url}", file=sys.stderr, flush=True)
            else:
                print(
                    "stale pidfile (process alive but URL silent); restarting",
                    file=sys.stderr,
                    flush=True,
                )
                pidfile.unlink(missing_ok=True)
        elif old_pid > 0 and _is_alive(old_pid) and old_study != str(study):
            _die(
                f"pidfile {pidfile} already supervises pid {old_pid} for {old_study}; "
                f"refusing to replace it for {study} (use --stop or another --pidfile)"
            )
        else:
            pidfile.unlink(missing_ok=True)

    if url is None:
        if port == 0:
            port = _pick_free_port()
        else:
            # Refuse to shadow a live listener on the requested port.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(1.0)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    _die(f"port {port} already answers; pass --port 0 or stop its owner first")
        url = f"http://127.0.0.1:{port}"
        log_path = record_dir / f"server-{port}.log"
        env = dict(os.environ)
        src = str(ROOT / "src")
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and DEFAULT_BROWSER_CACHE.is_dir():
            env["PLAYWRIGHT_BROWSERS_PATH"] = str(DEFAULT_BROWSER_CACHE)
        cmd = [sys.executable, "-m", "prc.cli", "eval-session", str(study), "--port", str(port)]
        # start_new_session detaches (setsid) so the hub survives the agent turn;
        # this is the background nohup equivalent with a pidfile for later --stop.
        with open(log_path, "ab", buffering=0) as log_handle:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
            )
        pid = int(proc.pid)
        _write_pidfile(
            pidfile,
            {"pid": pid, "port": port, "url": url, "study": str(study), "log": str(log_path)},
        )
        print(
            f"started supervised hub pid {pid} at {url} (log {log_path})",
            file=sys.stderr,
            flush=True,
        )
        if not _wait_for_url(url, timeout=float(args.timeout)):
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGTERM)
            pidfile.unlink(missing_ok=True)
            tail = ""
            with contextlib.suppress(OSError):
                tail = log_path.read_bytes()[-2000:].decode(errors="replace")
            _refuse(f"supervised hub pid {pid} never answered at {url}. Log tail: {tail[-500:]}")

    assert pid is not None and url is not None and log_path is not None
    checks: dict[str, dict[str, Any]] = {}
    page_errors: list[str] = []

    def _check(name: str, passed: bool, detail: str) -> None:
        checks[name] = {"pass": bool(passed), "detail": detail[:500]}

    # Baseline: the exact printed URL answers from the host.
    try:
        status, body = _http_get(url + "/api/state", timeout=5.0)
        _check(
            "server_answers",
            status == 200,
            f"GET /api/state -> {status} {body[:120].decode(errors='replace')}",
        )
    except Exception as err:
        _check("server_answers", False, f"{type(err).__name__}: {err}")

    try:
        before_hash = _session_hash(study)
        _check("study_snapshot", True, f"session.json sha256 {before_hash[:16]}")
    except OSError as err:
        before_hash = ""
        _check("study_snapshot", False, f"cannot read session.json: {err}")

    # Hold a silent preconnect socket open during the check. This is the exact
    # past failure: a browser-style connection that sends nothing once blocked
    # the single-threaded hub forever. The hub must keep answering afterwards.
    host, _, port_text = url.removeprefix("http://").partition(":")
    silent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    silent_open = False
    try:
        silent.settimeout(5.0)
        silent.connect((host, int(port_text)))
        silent.settimeout(None)
        silent_open = True
        _check(
            "silent_preconnect_held",
            True,
            "silent socket connected and held open with no bytes sent",
        )
    except OSError as err:
        _check("silent_preconnect_held", False, f"cannot open silent socket: {err}")

    screenshot_path: Path | None = None
    preview_ok = False
    try:
        if not silent_open:
            raise RuntimeError(
                "silent preconnect failed; refusing to hand off without the block check"
            )
        from playwright.sync_api import sync_playwright

        if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and DEFAULT_BROWSER_CACHE.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(DEFAULT_BROWSER_CACHE)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        screenshot_path = record_dir / f"handoff-{stamp}.png"
        with sync_playwright() as driver:
            try:
                browser = driver.chromium.launch()
            except Exception:
                browser = driver.chromium.launch(args=["--no-sandbox"])
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.on("pageerror", lambda err: page_errors.append(str(err)))
                # Load the exact URL that will be handed off, not a fixture copy.
                page.goto(url, timeout=15000)
                page.get_by_role("button", name=PREPARE_LABEL).wait_for(timeout=10000)
                _check("hub_renders", True, "exact URL renders with Prepare next reading visible")
                # Safe read-only interaction: Prepare shows the preview panel.
                # It must not start a trial or mutate the study (no Start click).
                page.get_by_role("button", name=PREPARE_LABEL).click()
                page.locator("#preview").wait_for(state="visible", timeout=10000)
                title_text = page.locator("#previewtitle").inner_text().strip()
                if title_text:
                    preview_ok = True
                    _check("preview_appears", True, "preview visible")
                else:
                    _check("preview_appears", False, "preview panel visible but title is empty")
                page.screenshot(path=str(screenshot_path))
                _check("screenshot_saved", screenshot_path.is_file(), str(screenshot_path))
            finally:
                browser.close()
    except Exception as err:
        if screenshot_path is None:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            screenshot_path = record_dir / f"handoff-{stamp}.png"
        _check(
            "hub_renders",
            checks.get("hub_renders", {}).get("pass", False),
            checks.get("hub_renders", {}).get("detail", f"{type(err).__name__}: {err}"),
        )
        if "preview_appears" not in checks:
            _check("preview_appears", False, f"{type(err).__name__}: {err}")
        if "screenshot_saved" not in checks:
            _check("screenshot_saved", False, f"{type(err).__name__}: {err}")
    finally:
        # Require the hub to keep answering while the silent socket stays open.
        try:
            started = time.monotonic()
            status, body = _http_get(url + "/api/state", timeout=5.0)
            elapsed = time.monotonic() - started
            if status == 200 and elapsed < 5.0:
                _check(
                    "silent_preconnect_survives",
                    True,
                    f"hub answered in {elapsed:.2f}s while silent socket held",
                )
            else:
                _check(
                    "silent_preconnect_survives",
                    False,
                    f"hub slow or bad while silent held: {status} in {elapsed:.2f}s",
                )
        except Exception as err:
            _check(
                "silent_preconnect_survives",
                False,
                f"{type(err).__name__}: {err} (silent connection blocked the hub)",
            )
        with contextlib.suppress(OSError):
            silent.close()

    _check(
        "no_page_errors",
        len(page_errors) == 0,
        "no page errors" if not page_errors else "; ".join(page_errors)[:400],
    )
    try:
        after_hash = _session_hash(study)
        _check(
            "read_only",
            after_hash == before_hash,
            f"session.json unchanged {after_hash[:16]}"
            if after_hash == before_hash
            else "session.json MUTATED by the handoff check",
        )
    except OSError as err:
        _check("read_only", False, f"cannot re-read session.json: {err}")

    passed = all(item["pass"] for item in checks.values()) and preview_ok
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    if screenshot_path is None:
        screenshot_path = record_dir / f"handoff-{stamp}.png"
    record_path = screenshot_path.with_suffix(".json")
    record = {
        "url": url,
        "port": port,
        "pid": pid,
        "pidfile": str(pidfile),
        "study": str(study),
        "screenshot": str(screenshot_path),
        "log": str(log_path),
        "preview": {"visible": preview_ok},
        "page_errors": page_errors,
        "checks": checks,
        "passed": passed,
        "created_at": datetime.now(UTC).isoformat(),
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    if not passed:
        failed = sorted(name for name, item in checks.items() if not item["pass"])
        _refuse(
            f"checks failed ({', '.join(failed)}); record kept at {record_path}, no URL printed"
        )

    # Success path only: print the exact handed-off URL to stdout.
    print(url, flush=True)
    print(f"handoff record: {record_path}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

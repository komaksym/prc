#!/usr/bin/env python3
"""Supervised handoff for the notes review hub.

Start or reuse one supervised hub process for the notes dir, detached from
the agent session so it survives after the turn ends (detached via
start_new_session, which calls setsid; equivalent to a background nohup
pidfile launch). Wait until the exact printed URL answers from the host.
Load that exact URL in a real browser (agent-browser CLI, isolated session)
and require the hub to render one PR section per roster.json entry. Drive read-only checks
(titles, GitHub hrefs, artifact answers) that must not mutate notes.json.
Hold a silent preconnect socket open during the check and require the hub
to keep answering afterwards. Write a handoff record under the record dir
with url, port, pid, pidfile, screenshot, and each check result. Refuse to
print a URL when any check fails: on failure this script exits nonzero with
HANDOFF REFUSED on stderr and prints no URL to stdout.
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
sys.path.insert(0, str(ROOT / "scripts"))
from verify_notes_hub import Browser  # noqa: E402

DEFAULT_RECORD_DIR = ROOT / "artifacts/study-v3/handoff/notes"
DEFAULT_PIDFILE = ROOT / "artifacts/study-v3/notes-hub.pid"


def _die(message: str, code: int = 1) -> None:
    print(f"handoff_study_hub: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _refuse(message: str) -> None:
    print(f"HANDOFF REFUSED: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _expected_pr_count(notes_dir: Path) -> int:
    """Return how many PR sections the hub must render: one per roster entry."""
    roster_path = notes_dir / "roster.json"
    try:
        roster = json.loads(roster_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        _refuse(f"cannot read roster {roster_path}: {err}")
    if not isinstance(roster, list) or not roster:
        _refuse(f"roster {roster_path} lists no PRs")
    return len(roster)


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
    tmp.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")
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


def _notes_hash(notes_dir: Path) -> str:
    target = notes_dir / "notes.json"
    if not target.is_file():
        return "absent"
    return hashlib.sha256(target.read_bytes()).hexdigest()


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
        description="Supervise one notes hub, prove the exact URL, record the handoff."
    )
    parser.add_argument("notes_dir", type=Path, help="notes dir with roster.json")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--pidfile", type=Path, default=DEFAULT_PIDFILE)
    parser.add_argument("--record-dir", type=Path, default=DEFAULT_RECORD_DIR)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--stop", action="store_true")
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
    notes_dir = Path(args.notes_dir).resolve()
    if not (notes_dir / "roster.json").is_file():
        _die(f"notes dir lacks roster.json: {notes_dir}")
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
        old_notes = stored.get("notes_dir")
        old_url = stored.get("url")
        old_port = stored.get("port")
        if old_pid > 0 and _is_alive(old_pid) and old_notes == str(notes_dir) and old_url:
            if _wait_for_url(str(old_url), timeout=5.0):
                pid, url = old_pid, str(old_url)
                port = int(old_port or 0)
                log_text = stored.get("log")
                log_path = Path(log_text) if log_text else record_dir / f"server-{port}.log"
                print(f"reusing supervised hub pid {pid} at {url}", file=sys.stderr, flush=True)
            else:
                print("stale pidfile; restarting", file=sys.stderr, flush=True)
                pidfile.unlink(missing_ok=True)
        elif old_pid > 0 and _is_alive(old_pid) and old_notes != str(notes_dir):
            _die(f"pidfile {pidfile} supervises pid {old_pid} for {old_notes}")
        else:
            pidfile.unlink(missing_ok=True)
    if url is None:
        if port == 0:
            port = _pick_free_port()
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(1.0)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    _die(f"port {port} already answers; pass --port 0 first")
        url = f"http://127.0.0.1:{port}"
        log_path = record_dir / f"server-{port}.log"
        env = dict(os.environ)
        src = str(ROOT / "src")
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
        cmd = [sys.executable, "-m", "prc.cli", "notes-review", str(notes_dir), "--port", str(port)]
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
            {
                "pid": pid,
                "port": port,
                "url": url,
                "notes_dir": str(notes_dir),
                "log": str(log_path),
            },
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
            _refuse(f"hub pid {pid} never answered at {url}. Log tail: {tail[-500:]}")
    assert pid is not None and url is not None and log_path is not None
    checks: dict[str, dict[str, Any]] = {}
    page_errors: list[str] = []
    expected = _expected_pr_count(notes_dir)

    def _check(name: str, passed: bool, detail: str) -> None:
        checks[name] = {"pass": bool(passed), "detail": detail[:500]}

    try:
        status, body = _http_get(url + "/api/state", timeout=5.0)
        state: dict[str, Any] = {}
        if status == 200:
            with contextlib.suppress(ValueError):
                state = json.loads(body.decode())
        prs = state.get("prs", []) if isinstance(state, dict) else []
        _check(
            "server_answers",
            status == 200 and len(prs) == expected,
            f"GET /api/state -> {status} with {len(prs)} PRs (roster lists {expected})",
        )
    except Exception as err:
        prs = []
        _check("server_answers", False, f"{type(err).__name__}: {err}")
    try:
        before_hash = _notes_hash(notes_dir)
        _check("notes_snapshot", True, f"notes.json sha256 {before_hash[:16]}")
    except OSError as err:
        before_hash = ""
        _check("notes_snapshot", False, f"cannot read notes.json: {err}")
    host, _, port_text = url.removeprefix("http://").partition(":")
    silent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    silent_open = False
    try:
        silent.settimeout(5.0)
        silent.connect((host, int(port_text)))
        silent.settimeout(None)
        silent_open = True
        _check("silent_preconnect_held", True, "silent socket held open, no bytes sent")
    except OSError as err:
        _check("silent_preconnect_held", False, f"cannot open silent socket: {err}")
    screenshot_path: Path | None = None
    titles_ok = False
    hrefs_ok = False
    artifacts_ok = False
    try:
        if not silent_open:
            raise RuntimeError("silent preconnect failed; refusing handoff")
        raw = subprocess.run(
            [
                "agent-browser",
                "session",
                "id",
                "--scope",
                "worktree",
                "--prefix",
                "handoffnotes-" + str(int(time.time())),
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not raw:
            raise RuntimeError("no isolated browser session")
        b = Browser(raw.split()[-1])
        try:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            screenshot_path = record_dir / f"handoff-{stamp}.png"
            b.run("set", "viewport", "1440", "900")
            b.run("open", url)
            b.run(
                "wait",
                "--fn",
                f'document.querySelectorAll("section[data-pr]").length >= {expected}',
            )
            section_count = b.js('document.querySelectorAll("section[data-pr]").length')
            first_title = b.js('document.querySelector("section[data-pr] h2").textContent')
            titles_ok = (
                section_count == expected
                and isinstance(first_title, str)
                and len(first_title.strip()) > 0
            )
            _check(
                "hub_renders",
                titles_ok,
                f"exact URL renders {section_count} PR sections",
            )
            hrefs = b.js(
                'Array.from(document.querySelectorAll("[data-github-link]"))'
                ".map(function(a){return a.href;})"
            )
            hrefs_ok = (
                isinstance(hrefs, list)
                and len(hrefs) == expected
                and all(
                    isinstance(h, str) and h.startswith("https://github.com/") and "/pull/" in h
                    for h in hrefs
                )
            )
            _check(
                "github_hrefs", hrefs_ok, f"{len(hrefs) if isinstance(hrefs, list) else 0} links"
            )
            missing = 0
            for pr in prs:
                code, _ = _http_get(url + pr["artifacts"]["infographic"], timeout=10.0)
                if code != 200:
                    missing += 1
            artifacts_ok = missing == 0 and len(prs) == expected
            _check(
                "artifacts_answer",
                artifacts_ok,
                f"{len(prs) - missing}/{expected} infographics answer",
            )
            errs = b.errors()
            page_errors.extend(errs)
            b.run("screenshot", str(screenshot_path))
            _check("screenshot_saved", screenshot_path.is_file(), str(screenshot_path))
        finally:
            with contextlib.suppress(Exception):
                subprocess.run(
                    ["agent-browser", "--session", b.session, "close"], capture_output=True
                )
    except Exception as err:
        if screenshot_path is None:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            screenshot_path = record_dir / f"handoff-{stamp}.png"
        if "hub_renders" not in checks:
            _check("hub_renders", False, f"{type(err).__name__}: {err}")
        if "screenshot_saved" not in checks:
            _check("screenshot_saved", False, f"{type(err).__name__}: {err}")
    finally:
        try:
            started = time.monotonic()
            status, _ = _http_get(url + "/api/state", timeout=5.0)
            elapsed = time.monotonic() - started
            _check(
                "silent_preconnect_survives",
                status == 200 and elapsed < 5.0,
                f"hub answered in {elapsed:.2f}s while silent socket held",
            )
        except Exception as err:
            _check("silent_preconnect_survives", False, f"{type(err).__name__}: {err}")
        with contextlib.suppress(OSError):
            silent.close()
    _check(
        "no_page_errors",
        len(page_errors) == 0,
        "no page errors" if not page_errors else "; ".join(page_errors)[:400],
    )
    try:
        after_hash = _notes_hash(notes_dir)
        _check(
            "read_only",
            after_hash == before_hash,
            "notes.json unchanged"
            if after_hash == before_hash
            else "notes.json MUTATED by the handoff check",
        )
    except OSError as err:
        _check("read_only", False, f"cannot re-read notes.json: {err}")
    passed = all(item["pass"] for item in checks.values()) and titles_ok and hrefs_ok
    passed = passed and artifacts_ok
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    if screenshot_path is None:
        screenshot_path = record_dir / f"handoff-{stamp}.png"
    record_path = screenshot_path.with_suffix(".json")
    record = {
        "url": url,
        "port": port,
        "pid": pid,
        "pidfile": str(pidfile),
        "notes_dir": str(notes_dir),
        "screenshot": str(screenshot_path),
        "log": str(log_path),
        "page_errors": page_errors,
        "checks": checks,
        "passed": passed,
        "created_at": datetime.now(UTC).isoformat(),
    }
    record_path.write_text(json.dumps(record, indent=2) + chr(10), encoding="utf-8")
    if not passed:
        failed = sorted(name for name, item in checks.items() if not item["pass"])
        _refuse(f"checks failed ({', '.join(failed)}); record at {record_path}")
    print(url, flush=True)
    print(f"handoff record: {record_path}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

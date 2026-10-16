"""Per-PR review hub: title, GitHub link, PRC artifacts, judge votes."""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from prc.evaluation import spotcheck


class NotesError(RuntimeError):
    """Notes roster or request failure."""


_ALLOWED_SUFFIXES = frozenset(
    {
        ".html",
        ".htm",
        ".svg",
        ".json",
        ".png",
        ".css",
        ".js",
        ".md",
        ".txt",
        ".webp",
        ".jpg",
        ".jpeg",
        ".mp4",
        ".wav",
    }
)

_ARTIFACT_FILES = ("infographic.png", "video.mp4", "page.html")
VERDICTS = frozenset({"right", "wrong", ""})


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise NotesError("cannot read " + str(path) + ": " + str(err)) from err


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + chr(10), encoding="utf-8")
    tmp.replace(path)


def github_url(pr_identity: str) -> str:
    repo, _, number = pr_identity.partition("#")
    return "https://github.com/" + repo + "/pull/" + number


class NotesStore:
    """Roster plus verdict JSON on disk; output dirs resolved at request time."""

    def __init__(self, notes_dir: Path) -> None:
        self.notes_dir = notes_dir.resolve()
        roster_raw = _load_json(self.notes_dir / "roster.json")
        if not isinstance(roster_raw, list) or not roster_raw:
            raise NotesError("roster.json must be a non-empty list")
        prepared_root = (self.notes_dir / "prepared_root").read_text(encoding="utf-8").strip()
        self.prepared_root = Path(prepared_root)
        if not self.prepared_root.is_absolute():
            self.prepared_root = (self.notes_dir / self.prepared_root).resolve()
        self.prs: list[dict[str, str]] = []
        for entry in roster_raw:
            pr_id = str(entry["id"])
            identity = str(entry["pr_identity"])
            self.prs.append({"id": pr_id, "pr_identity": identity, "title": str(entry["title"])})
        spot_path = self.notes_dir / "spotcheck.json"
        try:
            self.spotcheck: list[dict[str, Any]] = (
                spotcheck.validate(list(_load_json(spot_path))) if spot_path.is_file() else []
            )
        except spotcheck.SpotcheckError as error:
            raise NotesError(f"{spot_path}: {error}") from error
        self.notes_path = self.notes_dir / "notes.json"
        self._lock = threading.Lock()
        self.verdicts: dict[str, str] = {}
        self._read_verdicts()
        self.validate_outputs()

    def _read_verdicts(self) -> None:
        if not self.notes_path.is_file():
            self.verdicts = {}
            return
        raw = _load_json(self.notes_path)
        if not isinstance(raw, dict):
            raise NotesError("notes.json must be an object")
        known = {str(item["id"]) for item in self.spotcheck}
        verdicts = raw.get("verdicts", {})
        if isinstance(verdicts, dict):
            self.verdicts = {
                str(k): str(v) for k, v in verdicts.items() if k in known and v in VERDICTS and v
            }
        else:
            self.verdicts = {}

    def output_dir(self, pr_id: str) -> Path:
        identity_path = self.prepared_root / pr_id / "render-identity.json"
        raw = _load_json(identity_path)
        out = Path(str(raw["output"]))
        return out

    def validate_outputs(self) -> None:
        missing = []
        for pr in self.prs:
            out = self.output_dir(pr["id"])
            for name in _ARTIFACT_FILES:
                if not (out / name).is_file():
                    missing.append(pr["id"] + "/" + name)
        if missing:
            raise NotesError("PRC outputs missing: " + ", ".join(sorted(missing)))

    def public_state(self) -> dict[str, Any]:
        prs = []
        for pr in self.prs:
            pr_id = pr["id"]
            prs.append(
                {
                    "id": pr_id,
                    "pr_identity": pr["pr_identity"],
                    "title": pr["title"],
                    "github_url": github_url(pr["pr_identity"]),
                    "artifacts": {
                        "infographic": "/artifacts/" + pr_id + "/infographic.png",
                        "video": "/artifacts/" + pr_id + "/video.mp4",
                        "page": "/artifacts/" + pr_id + "/page.html",
                    },
                }
            )
        return {
            "prs": prs,
            "spotcheck": self.spotcheck,
            "verdicts": dict(self.verdicts),
        }

    def _write(self) -> None:
        _atomic_write_json(self.notes_path, {"verdicts": self.verdicts})

    def save_verdict(self, sentence_id: str, verdict: str) -> None:
        """Record whether the judge labeled one spot-check sentence right; "" clears it."""
        if sentence_id not in {str(item["id"]) for item in self.spotcheck}:
            raise KeyError(sentence_id)
        if verdict not in VERDICTS:
            raise NotesError("verdict must be right, wrong, or empty")
        with self._lock:
            if verdict:
                self.verdicts[sentence_id] = verdict
            else:
                self.verdicts.pop(sentence_id, None)
            self._write()


def _resolve_allowed(root: Path, relative: str) -> Path | None:
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if candidate.suffix.lower() not in _ALLOWED_SUFFIXES:
        return None
    if not candidate.is_file():
        return None
    return candidate


def serve(notes_dir: Path, port: int = 0) -> tuple[HTTPServer, str]:
    from prc.evaluation.assets import notes_page

    store = NotesStore(Path(notes_dir))
    request_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        timeout = 15

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: N802
            return

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            expected = "127.0.0.1:" + str(cast(HTTPServer, self.server).server_port)
            return origin == "http://" + expected and host == expected

        def do_GET(self) -> None:  # noqa: N802
            with request_lock:
                try:
                    self._get()
                except NotesError as error:
                    self._json(404, {"error": str(error)})
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    self.close_connection = True

        def do_POST(self) -> None:  # noqa: N802
            with request_lock:
                try:
                    self._post()
                except NotesError as error:
                    self._json(409, {"error": str(error)})

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                parsed = json.loads((raw or b"{}").decode())
            except (ValueError, UnicodeDecodeError) as error:
                raise NotesError("request must contain valid JSON") from error
            if not isinstance(parsed, dict):
                raise NotesError("request must be a JSON object")
            return parsed

        def _post(self) -> None:
            if not self._origin_ok():
                self._json(403, {"error": "cross-origin mutation refused"})
                return
            path = self.path.split("?", 1)[0]
            if path == "/api/verdict":
                payload = self._read_body()
                sentence_id = str(payload.get("id", ""))
                try:
                    store.save_verdict(sentence_id, str(payload.get("verdict", "")))
                except KeyError:
                    self._json(404, {"error": "unknown spot-check sentence: " + sentence_id})
                    return
                except NotesError as error:
                    self._json(400, {"error": str(error)})
                    return
                self._json(200, {"id": sentence_id, "verdict": store.verdicts.get(sentence_id, "")})
                return
            self._json(404, {"error": "not found"})

        def _get(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                html = notes_page(store.public_state()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return
            if path == "/api/state":
                self._json(200, store.public_state())
                return
            if path.startswith("/artifacts/"):
                rest = path[len("/artifacts/") :]
                pr_id, _, relative = rest.partition("/")
                if not pr_id or not relative or pr_id not in {pr["id"] for pr in store.prs}:
                    self._json(404, {"error": "not found"})
                    return
                try:
                    root = store.output_dir(pr_id)
                except NotesError as error:
                    self._json(404, {"error": str(error)})
                    return
                candidate = _resolve_allowed(root, relative)
                if candidate is None:
                    self._json(404, {"error": "not found"})
                    return
                content = candidate.read_bytes()
                mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                if candidate.suffix in (".html", ".htm"):
                    mime = "text/html; charset=utf-8"
                elif candidate.suffix == ".json":
                    mime = "application/json"
                elif candidate.suffix == ".png":
                    mime = "image/png"
                elif candidate.suffix == ".css":
                    mime = "text/css"
                elif candidate.suffix == ".js":
                    mime = "text/javascript"
                elif candidate.suffix in (".md", ".txt"):
                    mime = "text/plain; charset=utf-8"
                status = 200
                extra = ""
                wanted = self.headers.get("Range") or ""
                if wanted.startswith("bytes=") and "-" in wanted:
                    span = wanted[len("bytes=") :]
                    first_txt, _, last_txt = span.partition("-")
                    size = len(content)
                    try:
                        if first_txt:
                            first = int(first_txt)
                            last = min(int(last_txt) if last_txt else size - 1, size - 1)
                        else:
                            first, last = max(size - int(last_txt), 0), size - 1
                    except ValueError:
                        first, last, size = 0, -1, len(content)
                    if first >= size or first > last:
                        self.send_response(416)
                        self.send_header("Content-Range", "bytes */" + str(size))
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    status = 206
                    extra = "bytes " + str(first) + "-" + str(last) + "/" + str(size)
                    content = content[first : last + 1]
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Accept-Ranges", "bytes")
                if extra:
                    self.send_header("Content-Range", extra)
                if candidate.suffix in (".html", ".htm"):
                    self.send_header(
                        "Content-Security-Policy",
                        "default-src 'none'; script-src 'self' 'unsafe-inline'; "
                        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                        "media-src 'self'; font-src 'self' data:; "
                        "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox",
                    )
                    self.send_header("X-Frame-Options", "SAMEORIGIN")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            self._json(404, {"error": "not found"})

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    httpd = Server(("127.0.0.1", port), Handler)
    return httpd, "http://127.0.0.1:" + str(httpd.server_address[1])

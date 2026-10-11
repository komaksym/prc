"""Paired-eval session: server-owned trial state served over loopback HTTP."""

from __future__ import annotations

import fcntl
import json
import math
import mimetypes
import re
import subprocess
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, Any, cast


class SessionError(RuntimeError):
    """Session state or request failure."""


DEADLINE_SECONDS = 1200.0
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


def _now() -> float:
    return time.time()


def _json_dict(text: str) -> dict[str, Any]:
    parsed = json.loads(text)
    assert isinstance(parsed, dict)

    return parsed


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


class StudySession:
    """Loads, mutates, and persists session.json under an exclusive advisory lock."""

    def __init__(self, study_dir: Path) -> None:
        self.study_dir = study_dir.resolve()
        self.lock_path = self.study_dir / ".session.lock"
        self._lock_handle: IO[str] | None = None
        self.state: dict[str, Any] = {}
        self.open()

    def _read(self) -> dict[str, Any]:
        return _json_dict((self.study_dir / "session.json").read_text())

    def open(self) -> None:
        from prc.evaluation.kit import load_study

        self.study = load_study(self.study_dir).study
        self._lock_handle = self.lock_path.open("a+")
        try:
            fcntl.flock(self._lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise SessionError("another session writer holds this study") from error
        self.state = self._read()

    def persist(self) -> None:
        _atomic_write_json(self.study_dir / "session.json", self.state)

    def close(self) -> None:
        if self._lock_handle is not None:
            self._lock_handle.close()
            self._lock_handle = None

    # -- state helpers -------------------------------------------------

    def _trial(self, trial_id: str) -> dict[str, Any]:
        trial = self.state["trials"][trial_id]
        assert isinstance(trial, dict)

        return trial

    def _sweep_deadline(self) -> None:
        active_id = self.state.get("active_trial")
        if active_id is None:
            return
        trial = self._trial(active_id)
        started = self.state.get("started_at") or trial["started_at"]
        if started is None:
            return
        if _now() - float(started) >= DEADLINE_SECONDS:
            trial["state"] = "timed_out"
            trial["ended_at"] = float(started) + DEADLINE_SECONDS
            self.state["active_trial"] = None
            self.persist()

    def order_from_top(self) -> list[str]:
        return [str(trial_id) for trial_id in self.state["order"]]

    def next_trial(self) -> str | None:
        if self.state.get("closed"):
            return None
        for trial_id in self.order_from_top():
            if self._trial(trial_id)["state"] == "pending" and not self._trial(trial_id).get(
                "ineligible"
            ):
                return str(trial_id)

        return None

    def public_state(self) -> dict[str, Any]:
        self._sweep_deadline()
        active_id = self.state.get("active_trial")
        active: dict[str, Any] | None = None
        if active_id is not None:
            trial = self._trial(active_id)
            started = self.state.get("started_at") or trial["started_at"]
            elapsed = _now() - float(started)
            active = self._public_active(trial, elapsed)

        return {
            "closed": bool(self.state.get("closed")),
            "graded": bool(self.state.get("graded")),
            "active": active,
            "next": None if self.next_trial() is None else {"trial_id": "next"},
        }

    def _public_active(self, trial: dict[str, Any], elapsed: float) -> dict[str, Any]:
        study = _json_dict((self.study_dir / "study.json").read_text())
        questions = study["questions"][trial["snapshot_id"]]
        aid_kind = "prc" if trial["condition"] == "product" else "lens"

        return {
            "trial_id": trial["trial_id"],
            "state": trial["state"],
            "elapsed_seconds": elapsed,
            "remaining_seconds": max(0.0, DEADLINE_SECONDS - elapsed),
            "snapshot_title": study["snapshots"][trial["snapshot_id"]]["title"],
            "questions": [
                {
                    "qid": q["qid"],
                    "kind": q["kind"],
                    "prompt": q["prompt"],
                    "options": q.get("options"),
                }
                for q in questions
            ],
            "answers": trial["answers"],
            "confidence": trial["confidence"],
            "github_url": "https://github.com/"
            + study["snapshots"][trial["snapshot_id"]]["pr_identity"].replace("#", "/pull/")
            + "/files",
            "aid_url": f"/artifact/{trial['trial_id']}/aid/index.html",
            "aid_kind": aid_kind,
        }

    # -- state transitions ---------------------------------------------

    def start(self, report: dict[str, Any]) -> dict[str, Any]:
        from prc.evaluation.kit import load_study

        load_study(self.study_dir)
        self._sweep_deadline()
        self._require_reports(report)
        if self.state.get("active_trial") is not None:
            raise SessionError("a trial is already active; one reading at a time")
        if self.state.get("closed"):
            raise SessionError("study is closed")
        trial_id = self.next_trial()
        if trial_id is None:
            raise SessionError("no pending trials remain")
        trial = self._trial(trial_id)
        if report.get("trial_id") != trial_id:
            raise SessionError("reading changed; prepare the current reading again")
        if report["familiarity"]["seen_before"] or report["cross_tool_exposure"]["saw_other_aid"]:
            trial["familiarity"] = report["familiarity"]
            trial["cross_exposure_start"] = report["cross_tool_exposure"]
            trial["ineligible"] = "prior familiarity or prior explanation exposure"
            self.persist()
            raise SessionError("familiar PR retained as unknown; timed reading refused")
        if self.study["sealed"]["payload"].get("study_mode", "real") == "real":
            _verify_live(self.study["snapshots"][trial["snapshot_id"]])
        trial["state"] = "active"
        trial["started_at"] = _now()
        trial["familiarity"] = report["familiarity"]
        trial["cross_exposure_start"] = report["cross_tool_exposure"]
        self.state["active_trial"] = trial_id
        self.state["started_at"] = trial["started_at"]
        self.persist()

        return self._public_active(trial, 0.0)

    def save_answers(
        self, answers: dict[str, str], confidence: dict[str, float], trial_id: str
    ) -> None:
        self._sweep_deadline()
        active_id = self.state.get("active_trial")
        if active_id is None:
            raise SessionError("no active trial to save into")
        if trial_id != active_id:
            raise SessionError("stale reading request")
        trial = self._trial(active_id)
        questions = self._questions(trial)
        qids = {q["qid"] for q in questions}
        unknown = set(answers) - qids
        if unknown or set(confidence) - qids:
            raise SessionError("unknown qids in answers")
        for q in questions:
            value = answers.get(q["qid"])
            if value is not None and (
                not isinstance(value, str)
                or (q["kind"] == "multiple_choice" and value != "" and value not in q["options"])
            ):
                raise SessionError("answer must be text or a listed option")
        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or not 0 <= v <= 100
            for v in confidence.values()
        ):
            raise SessionError("confidence must be between 0 and 100")
        trial["answers"].update(answers)
        trial["confidence"].update(confidence)
        self.persist()

    def _questions(self, trial: dict[str, Any]) -> list[dict[str, Any]]:
        study = _json_dict((self.study_dir / "study.json").read_text())

        return [dict(q) for q in study["questions"][trial["snapshot_id"]]]

    def submit(self, report: dict[str, Any]) -> None:
        self._finish("submitted", report)

    def abort(self, report: dict[str, Any]) -> None:
        self._finish("aborted", report)

    def _finish(self, outcome: str, report: dict[str, Any]) -> None:
        self._sweep_deadline()
        active_id = self.state.get("active_trial")
        if active_id is None:
            raise SessionError("no active trial to finish")
        if report.get("trial_id") != active_id:
            raise SessionError("stale reading request")
        exposure = report.get("cross_tool_exposure")
        if not isinstance(exposure, dict) or not isinstance(exposure.get("saw_other_aid"), bool):
            raise SessionError("cross-tool exposure report is required at completion")
        if "answers" in report:
            self.save_answers(report["answers"], report.get("confidence", {}), active_id)
        trial = self._trial(active_id)
        trial["cross_exposure_submit"] = report.get("cross_tool_exposure")
        trial["state"] = outcome
        trial["ended_at"] = _now()
        self.state["started_at"] = None
        self.state["active_trial"] = None
        self.persist()

    def close_study(self) -> None:
        self._sweep_deadline()
        if self.state.get("active_trial") is not None:
            raise SessionError("close refuses while a trial is active; submit or abort first")
        if self.state.get("closed"):
            raise SessionError("study is already closed")
        self.state["closed"] = True
        self.persist()

    def _require_closed(self) -> None:
        if self.state.get("closed") is not True:
            raise SessionError("grading and analysis require a closed study")

    def grading(self) -> dict[str, Any]:
        """Persist the condition-blinded sheet only after all readings are frozen."""
        from prc.evaluation.kit import KitError, export_blinded

        self._require_closed()
        try:
            return export_blinded(self.study_dir, self.study_dir / "grading.json")
        except KitError as error:
            raise SessionError(str(error)) from error

    def grade(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate exact grades, then publish recorded outcomes and pilot analysis."""
        from prc.evaluation.analysis import analyze
        from prc.evaluation.io import load_pairs_with_protocol
        from prc.evaluation.kit import KitError, apply_scores

        self._require_closed()
        scores = payload.get("scores")
        if not isinstance(scores, dict) or any(
            not isinstance(awarded, dict) for awarded in scores.values()
        ):
            raise SessionError("scores must map trial IDs to question scores")
        document = {"study_digest": payload.get("study_digest"), "scores": scores}
        with TemporaryDirectory(prefix=".grading-", dir=self.study_dir) as staging:
            root = Path(staging)
            _atomic_write_json(root / "scores.json", document)
            try:
                results = apply_scores(self.study_dir, root / "scores.json", root / "results.json")
                pairs, protocol = load_pairs_with_protocol(root / "results.json")
                if protocol is None:
                    raise SessionError("graded results require the frozen protocol")
                report = dict(asdict(analyze(pairs, protocol)))
            except (KitError, ValueError) as error:
                raise SessionError(str(error)) from error
            for field in ("study_digest", "interpretation", "deviations"):
                report[field] = results[field]
            _atomic_write_json(root / "analysis.json", report)
            for name in ("scores.json", "results.json", "analysis.json"):
                (root / name).replace(self.study_dir / name)
        self.state["graded"] = True
        self.persist()
        return report

    def analysis(self) -> dict[str, Any]:
        self._require_closed()
        if self.state.get("graded") is not True:
            raise SessionError("save all grades before viewing analysis")
        return _json_dict((self.study_dir / "analysis.json").read_text())

    def _require_reports(self, report: dict[str, Any]) -> None:
        for role in ("familiarity", "cross_tool_exposure"):
            value = report.get(role)
            if not isinstance(value, dict) or not isinstance(
                value.get("seen_before" if role == "familiarity" else "saw_other_aid"), bool
            ):
                raise SessionError(f"the {role} report is required before content")

    # -- artifact serving ----------------------------------------------

    def active_trees(self) -> tuple[Path, str] | None:
        self._sweep_deadline()
        active_id = self.state.get("active_trial")
        if active_id is None:
            return None
        trial = self._trial(active_id)
        aid = "prc" if trial["condition"] == "product" else "lens"

        return self.study_dir / "snapshots" / trial["snapshot_id"], aid

    def preview(self) -> dict[str, Any]:
        trial_id = self.next_trial()
        if trial_id is None or self.state.get("active_trial") is not None:
            raise SessionError("no reading is available to prepare")
        meta = self.study["snapshots"][self._trial(trial_id)["snapshot_id"]]
        return {
            "trial_id": trial_id,
            "pr_identity": meta["pr_identity"],
            "title": meta["title"],
            "head_sha": meta["head_sha"],
        }


def _verify_live(meta: dict[str, Any]) -> None:
    identity = meta["pr_identity"]
    repo, number = identity.split("#")
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{number}"],
            capture_output=True,
            timeout=20,
            check=True,
        )
        if json.loads(result.stdout)["head"]["sha"] != meta["head_sha"]:
            raise SessionError("live GitHub head changed; reading refused")
        lens = meta["lens"]
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/comments/{lens['comment_id']}"],
            capture_output=True,
            timeout=20,
            check=True,
        )
        comment = json.loads(result.stdout)
        import hashlib

        if hashlib.sha256(comment["body"].encode()).hexdigest() != meta["lens_body_sha256"]:
            raise SessionError("live Lens comment changed; reading refused")
    except (OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        raise SessionError(
            "cannot verify live GitHub and Lens revisions; reading refused"
        ) from error


def _resolve_allowed(root: Path, relative: str) -> Path | None:
    root = root.resolve()
    candidate = (root / relative).resolve()
    if root not in candidate.parents and candidate != root:
        return None
    if candidate.suffix.lower() not in _ALLOWED_SUFFIXES:
        return None
    if not candidate.is_file():
        return None

    return candidate


def serve(study_dir: Path, port: int = 0) -> tuple[HTTPServer, str]:
    from prc.evaluation.kit import load_study

    load_study(study_dir)
    study_path = study_dir.resolve()
    current = StudySession(study_path)

    class Handler(BaseHTTPRequestHandler):
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

        def _kv(self, method: str) -> StudySession:
            return current

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")

            expected = f"127.0.0.1:{cast(HTTPServer, self.server).server_port}"
            return origin == f"http://{expected}" and host == expected

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._get()
            except SessionError as error:
                self._json(403, {"error": str(error)})
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._post()
            except SessionError as error:
                self._json(409 if "close" not in str(error) else 409, {"error": str(error)})

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"

            try:
                parsed = json.loads((raw or b"{}").decode())
            except (ValueError, UnicodeDecodeError) as error:
                raise SessionError("request must contain valid JSON") from error
            if not isinstance(parsed, dict):
                raise SessionError("request must be a JSON object")
            return parsed

        def _post(self) -> None:
            if not self._origin_ok():
                self._json(403, {"error": "cross-origin mutation refused"})

                return
            s = self._kv("POST")
            path = self.path.split("?", 1)[0]
            if path == "/api/start":
                self._json(200, s.start(self._read_body()))
                return
            if path == "/api/answers":
                payload = self._read_body()
                s.save_answers(
                    payload.get("answers") or {},
                    payload.get("confidence") or {},
                    str(payload.get("trial_id", "")),
                )
                self._json(200, s.public_state())
                return
            if path == "/api/submit":
                s.submit(self._read_body())
                self._json(200, s.public_state())
                return
            if path == "/api/abort":
                s.abort(self._read_body())
                self._json(200, s.public_state())
                return
            if path == "/api/close":
                try:
                    s.close_study()
                except SessionError:
                    self._json(409, {"error": "close refused"})
                    return
                self._json(200, s.public_state())
                return
            if path == "/api/grade":
                self._json(200, s.grade(self._read_body()))
                return

            self._json(404, {"error": "not found"})

        def _get(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                from prc.evaluation.assets import study_page

                html = study_page().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return
            if path == "/api/state":
                self._json(200, self._kv("GET").public_state())
                return
            if path == "/api/preview":
                self._json(200, current.preview())
                return
            if path == "/api/grading":
                self._json(200, current.grading())
                return
            if path == "/api/analysis":
                self._json(200, current.analysis())
                return

            trees = self._kv("GET").active_trees()
            path = path.removeprefix("/artifact/")
            bound_id, _, path = path.partition("/")
            if bound_id != current.state.get("active_trial"):
                self._json(404, {"error": "not found"})
                return
            kind, _, relative = path.partition("/")
            if trees is None or kind not in ("github", "aid") or relative == "":
                self._json(404, {"error": "not found"})
                return
            root, aid = trees
            target_root = root / "github" if kind == "github" else root / aid
            candidate = _resolve_allowed(target_root, relative)
            if candidate is None:
                self._json(404, {"error": "not found"})
                return
            content = candidate.read_bytes()
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            if candidate.suffix in (".html", ".htm"):
                mime = "text/html; charset=utf-8"
            elif candidate.suffix == ".json":
                mime = "application/json"
            elif candidate.suffix in (".png", ".webp", ".jpg", ".jpeg"):
                mime = "image/" + candidate.suffix.lstrip(".")
            elif candidate.suffix == ".css":
                mime = "text/css"
            elif candidate.suffix == ".js":
                mime = "text/javascript"
            elif candidate.suffix in (".md", ".txt"):
                mime = "text/plain; charset=utf-8"
            status, content_range = 200, None
            wanted = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
            if wanted and wanted.group(1) + wanted.group(2):
                size = len(content)
                if wanted.group(1):
                    first = int(wanted.group(1))
                    last = min(int(wanted.group(2) or size - 1), size - 1)
                else:
                    first, last = max(size - int(wanted.group(2)), 0), size - 1
                if first >= size or first > last:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status, content_range = 206, f"bytes {first}-{last}/{size}"
                content = content[first : last + 1]
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Accept-Ranges", "bytes")
            if content_range:
                self.send_header("Content-Range", content_range)
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; font-src 'self' data:; sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox",
            )
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    class Server(HTTPServer):
        def server_close(self) -> None:
            super().server_close()
            current.close()

    httpd = Server(("127.0.0.1", port), Handler)

    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"

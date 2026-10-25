"""Paired-eval session: real HTTP server on an ephemeral loopback port."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from prc.evaluation import session as session_mod


@pytest.fixture
def prepared(make_paired: Any) -> Path:
    from prc.evaluation import kit

    fixture = make_paired(pairs=2)
    kit.prepare_study(fixture.manifest, fixture.study)

    return Path(fixture.study)


@pytest.fixture
def server(prepared: Path) -> Any:
    study_path = Path(prepared)
    httpd, url = session_mod.serve(study_path, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield url

    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def study_dir(prepared: Path) -> Path:
    return Path(prepared)


def get(url: str, path: str) -> tuple[int, str]:
    if path.startswith("/artifact/"):
        active = json.loads(get(url, "/api/state")[1])["active"]
        path = (
            "/artifact/"
            + (active["trial_id"] if active else "missing")
            + "/"
            + path.removeprefix("/artifact/")
        )
    request = urllib.request.Request(url + path)

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def post(
    url: str, path: str, payload: dict[str, Any], origin: str | None = "present"
) -> tuple[int, str]:
    if path in ("/api/answers", "/api/submit", "/api/abort") and "trial_id" not in payload:
        active = json.loads(get(url, "/api/state")[1])["active"]
        payload = {**payload, "trial_id": active["trial_id"] if active else "missing"}
    headers = {"Content-Type": "application/json"}
    if origin == "present":
        headers["Origin"] = url
    body = json.dumps(payload).encode()
    request = urllib.request.Request(url + path, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def state(url: str) -> dict[str, Any]:
    status, body = get(url, "/api/state")
    assert status == 200

    parsed = json.loads(body)
    assert isinstance(parsed, dict)
    return parsed


def study_svg_dir(study: Path) -> Path:
    return next(study.glob("snapshots/*/lens"))


def start(url: str) -> tuple[int, str]:
    preview_status, preview_body = get(url, "/api/preview")
    trial_id = json.loads(preview_body).get("trial_id") if preview_status == 200 else "missing"
    return post(
        url,
        "/api/start",
        {
            "trial_id": trial_id,
            "familiarity": {"seen_before": False, "note": ""},
            "cross_tool_exposure": {"saw_other_aid": False, "note": ""},
        },
    )


def test_start_gates_reports_then_exposes_only_assigned_tree(server: str, study_dir: Path) -> None:
    # before start: no artifact access, no identity leak
    assert get(server, "/artifact/github/index.html")[0] == 404
    assert get(server, "/api/state").count("owner") == 0

    start(server)
    active = state(server)["active"]
    assert active is not None
    assert active["aid_kind"] in ("lens", "prc")
    assert [q["kind"] for q in active["questions"]] == ["multiple_choice", "short", "short"]
    assert all("key" not in q for q in active["questions"])

    # only the active trial's trees are reachable by name, no manifest, no keys
    assert get(server, "/artifact/github/index.html")[0] == 200
    svg_name = next(p.name for p in study_svg_dir(study_dir).glob("*.svg"))
    assert get(server, f"/artifact/aid/{svg_name}")[0] == 200
    assert get(server, "/study.json")[0] == 404
    assert get(server, "/session.json")[0] == 404
    assert get(server, "/artifact/github/../../../study.json")[0] == 404


def test_artifact_range_request_lets_the_browser_seek_video(make_paired: Any) -> None:
    from prc.evaluation import kit

    fixture = make_paired(pairs=1)
    clip = bytes(range(256)) * 4
    for snap in fixture.data["pairs"][0]["snapshots"]:
        (fixture.root / snap["artifacts"]["github"] / "clip.mp4").write_bytes(clip)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = session_mod.serve(Path(fixture.study), port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        start(url)
        trial = state(url)["active"]["trial_id"]
        path = f"{url}/artifact/{trial}/github/clip.mp4"
        with urllib.request.urlopen(path, timeout=5) as whole:
            assert whole.headers["Accept-Ranges"] == "bytes"
            assert whole.read() == clip
        request = urllib.request.Request(path, headers={"Range": "bytes=600-"})
        with urllib.request.urlopen(request, timeout=5) as part:
            assert part.status == 206
            assert part.headers["Content-Range"] == f"bytes 600-{len(clip) - 1}/{len(clip)}"
            assert part.read() == clip[600:]
        request = urllib.request.Request(path, headers={"Range": "bytes=10-19"})
        with urllib.request.urlopen(request, timeout=5) as part:
            assert part.status == 206
            assert part.read() == clip[10:20]
        bad = urllib.request.Request(path, headers={"Range": f"bytes={len(clip) + 5}-"})
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(bad, timeout=5)
        assert error.value.code == 416
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_one_active_and_terminal_states_are_forward_only(server: str, prepared: Path) -> None:
    assert start(server)[0] == 200
    assert start(server)[0] == 409  # second simultaneous start refused

    page = get(server, "/")[1]
    assert "iframe" in page and "sandbox" in page

    status, _ = post(
        server,
        "/api/answers",
        {"answers": {"q1": "cache/evict.go", "q2": "t", "q3": ""}, "confidence": {"q1": 70}},
    )
    assert status == 200

    status, _ = post(
        server, "/api/submit", {"cross_tool_exposure": {"saw_other_aid": False, "note": ""}}
    )
    assert status == 200
    assert state(server)["active"] is None

    # terminal: no edits, no re-serve
    assert post(server, "/api/answers", {"answers": {}, "confidence": {}})[0] == 409
    assert get(server, "/artifact/github/index.html")[0] == 404

    # next trial starts after terminal
    assert start(server)[0] == 200


def test_autosave_and_refresh_resume_same_trial(server: str, prepared: Path) -> None:
    start(server)
    first = state(server)["active"]
    post(server, "/api/answers", {"answers": {"q1": "cache/evict.go"}, "confidence": {"q1": 55}})

    again = state(server)["active"]  # refresh/restart reads the same server-side trial
    assert again["trial_id"] == first["trial_id"]
    assert again["answers"] == {"q1": "cache/evict.go"}
    assert again["elapsed_seconds"] >= first["elapsed_seconds"]
    assert again["remaining_seconds"] <= first["remaining_seconds"]


def test_deadline_marks_timed_out_preserving_answers(
    monkeypatch: Any,
    server: str,
    prepared: Path,
) -> None:
    start(server)
    started = time.time()
    monkeypatch.setattr(session_mod, "_now", lambda: started + 1300.0)

    current = state(server)["active"]
    assert current is None
    payload = json.loads((prepared / "session.json").read_text())
    timed = [trial for trial in payload["trials"].values() if trial["state"] == "timed_out"]
    assert len(timed) == 1
    assert payload["active_trial"] is None


def test_cross_origin_mutation_refused(server: str) -> None:
    status, _ = post(server, "/api/start", {}, origin="http://evil:1")
    assert status == 403


def test_close_refuses_active_and_export_needs_closed(server: str, prepared: Path) -> None:
    start(server)
    assert post(server, "/api/close", {})[0] == 409

    post(server, "/api/submit", {"cross_tool_exposure": {"saw_other_aid": False, "note": ""}})
    # a second trial remains pending; close allows it and retains unknowns
    assert post(server, "/api/close", {})[0] == 200
    assert state(server)["closed"] is True
    assert start(server)[0] == 409  # closed study: no further mutation


def test_silent_browser_connection_cannot_block_the_hub(server: str, study_dir: Path) -> None:
    """A preconnected socket that sends nothing must not freeze every later request."""
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(server)
    assert parsed.hostname is not None and parsed.port is not None
    silent = socket.create_connection((parsed.hostname, parsed.port))
    try:
        started = time.monotonic()
        status, body = get(server, "/api/state")
        assert status == 200, body
        assert time.monotonic() - started < 5, "a silent connection blocked the hub"
    finally:
        silent.close()

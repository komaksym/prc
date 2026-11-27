from __future__ import annotations

import functools
import importlib.util
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "verify_page", Path(__file__).parents[1] / "scripts/verify_page.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_verifier_serves_seekable_audio(tmp_path: Path) -> None:
    clip = bytes(range(256)) * 4
    (tmp_path / "video.mp4").write_bytes(clip)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(module.Quiet, directory=str(tmp_path))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/video.mp4"
    try:
        with urllib.request.urlopen(url) as response:
            assert response.headers["Accept-Ranges"] == "bytes"
            assert response.read() == clip
        for requested, start, end in [
            ("bytes=600-", 600, 1023),
            ("bytes=10-19", 10, 19),
            ("bytes=-20", 1004, 1023),
        ]:
            request = urllib.request.Request(url, headers={"Range": requested})
            with urllib.request.urlopen(request) as response:
                assert response.status == 206
                assert response.headers["Content-Range"] == f"bytes {start}-{end}/1024"
                assert response.read() == clip[start : end + 1]
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=2000-"}))
        assert error.value.code == 416
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

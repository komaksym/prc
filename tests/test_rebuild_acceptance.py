from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rebuild_records_current_outputs_with_relative_cli_and_wheel(tmp_path: Path) -> None:
    case = tmp_path / "acceptance" / "demo"
    case.mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    out = case / "output"
    out.mkdir()
    (out / "map.html").write_text("previous render")
    old = {
        "cwd": str(work),
        "out": str(out),
        "command": ["old-prc", "explain", "--out", str(out)],
        "output_hashes": {"map.html": "stale", "infographic.png": "obsolete"},
        "proof": "old-proof",
        "completed_at": "2000-01-01T00:00:00+00:00",
    }
    (case / "render-identity.json").write_text(json.dumps(old))
    prc = tmp_path / "fake-prc"
    prc.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == 'explain':\n"
        "    out = Path(sys.argv[sys.argv.index('--out') + 1])\n"
        "    out.mkdir(parents=True)\n"
        "    (out / 'map.html').write_text('current render')\n"
        "    (out / 'card.png').write_bytes(b'new card')\n"
        "    print(json.dumps({'out': str(out)}))\n"
        "else:\n"
        "    (Path(sys.argv[2]) / 'listening.json').write_text('{\"passed\": true}')\n"
    )
    prc.chmod(0o755)
    wheel = tmp_path / "proof" / "dist" / "test.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel")
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/rebuild_acceptance.py"),
            "acceptance",
            "--prc",
            "fake-prc",
            "--wheel",
            "proof/dist/test.whl",
            "--commit",
            "current-commit",
            "--before",
            "previous",
            "demo",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    identity = json.loads((case / "render-identity.json").read_text())
    assert identity["command"][0] == str(prc)
    assert identity["wheel"] == str(wheel)
    assert identity["proof"] == str(wheel.parent.parent)
    assert identity["completed_at"] > identity["started_at"]
    assert identity["prc_commit"] == "current-commit"
    assert "infographic.png" not in identity["output_hashes"]
    for name in ("map.html", "listening.json", "card.png"):
        assert (
            identity["output_hashes"][name] == hashlib.sha256((out / name).read_bytes()).hexdigest()
        )
    assert (case.parent / "before-previous/demo/output/map.html").read_text() == "previous render"

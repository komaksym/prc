from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "prc" / "presentation" / "map_assets"
BUNDLE = "prlens.bundle.js"
LOCK = "prlens.lock.json"
TARBALLS = Path(os.environ.get("PRC_VENDOR_TARBALLS", "."))
NODE_MODULES = Path(os.environ.get("PRC_VENDOR_NODE_MODULES", "."))


def _node() -> str:
    exe = shutil.which("node")
    assert exe is not None, "maintainer vendoring checks need Node.js"
    return exe


def _offline_inputs() -> None:
    tarball = TARBALLS / "coldtea-pr-lens-renderer-0.3.2.tgz"
    assert tarball.exists(), "set PRC_VENDOR_TARBALLS to the pinned tarball directory"
    assert (NODE_MODULES / "esbuild").exists(), (
        "set PRC_VENDOR_NODE_MODULES to the pinned dev dependencies"
    )


def _stage(tmp_path: Path) -> Path:
    stage = tmp_path / "repo"
    (stage / "scripts").mkdir(parents=True)
    asset_dir = stage / "src" / "prc" / "presentation" / "map_assets"
    asset_dir.mkdir(parents=True)
    (stage / "tests" / "data").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "vendor-prlens.mjs", stage / "scripts" / "vendor-prlens.mjs")
    for name in (BUNDLE, LOCK):
        shutil.copy(ASSETS / name, asset_dir / name)
    shutil.copytree(ROOT / "tests" / "data" / "graphdoc", stage / "tests" / "data" / "graphdoc")
    return stage


def _revendor(stage: Path, *flags: str) -> subprocess.CompletedProcess[bytes]:
    _offline_inputs()
    return subprocess.run(
        [
            _node(),
            str(stage / "scripts" / "vendor-prlens.mjs"),
            "--tarballs",
            str(TARBALLS),
            "--node-modules",
            str(NODE_MODULES),
            *flags,
        ],
        capture_output=True,
        timeout=300,
    )


def _asset_sha(stage: Path, name: str) -> str:
    data = (stage / "src" / "prc" / "presentation" / "map_assets" / name).read_bytes()
    return hashlib.sha256(data).hexdigest()


def test_revendoring_without_update_reproduces_pinned_bytes(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    before = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}

    result = _revendor(stage)

    assert result.returncode == 0, result.stderr.decode()
    after = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}
    assert after == before, "no-update re-vendor rewrote vendored artifacts"


def test_revendoring_without_update_rejects_bundle_mismatch(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    lock_path = stage / "src" / "prc" / "presentation" / "map_assets" / LOCK
    lock = json.loads(lock_path.read_text())
    lock["bundle_sha256"] = "0" * 64
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    before = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}

    result = _revendor(stage)

    assert result.returncode != 0
    assert "bundle_sha256 mismatch against prlens.lock.json" in result.stderr.decode()
    after = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}
    assert after == before, "mismatch run wrote bundle or lock"


def test_revendoring_without_update_rejects_golden_mismatch(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    lock_path = stage / "src" / "prc" / "presentation" / "map_assets" / LOCK
    lock = json.loads(lock_path.read_text())
    lock["validated_goldens"]["shop.json"] = "0" * 64
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    before = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}

    result = _revendor(stage)

    assert result.returncode != 0
    assert "validated_goldens mismatch against prlens.lock.json" in result.stderr.decode()
    after = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}
    assert after == before, "golden mismatch run wrote bundle or lock"


def test_update_refreshes_bundle_pin(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    lock_path = stage / "src" / "prc" / "presentation" / "map_assets" / LOCK
    lock = json.loads(lock_path.read_text())
    lock["bundle_sha256"] = "0" * 64
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")

    result = _revendor(stage, "--update")

    assert result.returncode == 0, result.stderr.decode()
    lock = json.loads((stage / "src" / "prc" / "presentation" / "map_assets" / LOCK).read_text())
    actual_bundle = _asset_sha(stage, BUNDLE)
    assert lock["bundle_sha256"] == actual_bundle


def test_tarball_mismatch_rejects_without_writes(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    lock_path = stage / "src" / "prc" / "presentation" / "map_assets" / LOCK
    lock = json.loads(lock_path.read_text())
    lock["tarball_sha256"]["renderer"] = "1" * 64
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    before = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}

    result = _revendor(stage)

    assert result.returncode != 0
    assert "tarball hash mismatch against prlens.lock.json" in result.stderr.decode()
    after = {name: _asset_sha(stage, name) for name in (BUNDLE, LOCK)}
    assert after == before, "tarball mismatch run wrote bundle or lock"

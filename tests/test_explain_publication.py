"""Publication failures must preserve the previous complete artifact."""

import shutil
from pathlib import Path

import pytest

from prc import pipeline


def test_complete_generation_replaces_old_media(tmp_path: Path) -> None:
    target = tmp_path / "published"
    target.mkdir()
    (target / "video.mp4").write_bytes(b"previous video")
    work = tmp_path / "work"
    work.mkdir()
    (work / "map.json").write_bytes(b"new map")
    pipeline._publish_explain(work, target)
    assert {p.name: p.read_bytes() for p in target.iterdir()} == {"map.json": b"new map"}
    assert not work.exists()


@pytest.mark.parametrize("restore_fails", [False, True])
def test_failed_publication_preserves_previous_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_fails: bool
) -> None:
    target = tmp_path / "published"
    target.mkdir()
    (target / "video.mp4").write_bytes(b"previous video")
    work = tmp_path / "work"
    work.mkdir()
    (work / "map.json").write_bytes(b"new map")
    rename = Path.rename

    def fail(self: Path, destination: Path) -> Path:
        if self == work or (restore_fails and self.name == "previous"):
            raise OSError("simulated rename failure")
        return rename(self, destination)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises((OSError, RuntimeError), match="rename failure|recover"):
        pipeline._publish_explain(work, target)
    previous = list(tmp_path.rglob("video.mp4"))
    assert len(previous) == 1
    assert previous[0].read_bytes() == b"previous video"
    assert (work / "map.json").read_bytes() == b"new map"
    if not restore_fails:
        assert previous[0] == target / "video.mp4"


def test_concurrent_publication_refuses_an_occupied_lock(tmp_path: Path) -> None:
    target = tmp_path / "published"
    target.mkdir()
    (target / "map.json").write_bytes(b"previous map")
    work = tmp_path / "work"
    work.mkdir()
    lock = tmp_path / ".published.lock"
    lock.mkdir()
    with pytest.raises(FileExistsError):
        pipeline._publish_explain(work, target)
    assert (target / "map.json").read_bytes() == b"previous map"
    assert lock.is_dir()


def test_publication_refuses_a_symlink(tmp_path: Path) -> None:
    previous = tmp_path / "previous-artifact"
    previous.mkdir()
    (previous / "map.json").write_bytes(b"previous map")
    target = tmp_path / "published"
    target.symlink_to(previous, target_is_directory=True)
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises((OSError, RuntimeError), match="directory|symlink"):
        pipeline._publish_explain(work, target)
    assert target.is_symlink()
    assert (previous / "map.json").read_bytes() == b"previous map"


@pytest.mark.parametrize("cleanup", ["backup", "lock"])
def test_cleanup_failure_reports_committed_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cleanup: str,
) -> None:
    target = tmp_path / "published"
    target.mkdir()
    (target / "video.mp4").write_bytes(b"previous video")
    work = tmp_path / "work"
    work.mkdir()
    (work / "map.json").write_bytes(b"new map")

    def fail_backup(path: Path) -> None:
        raise OSError("backup cleanup failed")

    rmdir = Path.rmdir

    def fail_lock(self: Path) -> None:
        if self.name == ".published.lock":
            raise OSError("lock cleanup failed")
        rmdir(self)

    if cleanup == "backup":
        monkeypatch.setattr(shutil, "rmtree", fail_backup)
    else:
        monkeypatch.setattr(Path, "rmdir", fail_lock)
    pipeline._publish_explain(work, target)
    assert (target / "map.json").read_bytes() == b"new map"
    assert not (target / "video.mp4").exists()
    output = capsys.readouterr()
    assert output.out == ""
    assert "cleanup failed" in output.err

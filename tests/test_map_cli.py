from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from map_sample import shop_map
from prc import cli, pipeline
from prc.brief import Brief
from prc.changemap import ChangeMap
from prc.fixture_source import FixtureSource
from prc.github_source import GitHubSource
from prc.model import PrRef
from prc.snapshot import Acquisition
from prc.verification import EligibilityPolicy

from conftest import FakeClock


@pytest.fixture
def built(monkeypatch: pytest.MonkeyPatch) -> list[Brief]:
    """Stands in for the domain builder; records the brief it was handed."""

    seen: list[Brief] = []

    def build(acquisition: Acquisition, repo: Path, brief: Brief) -> ChangeMap:
        assert repo.exists() and acquisition.snapshot.comparison.head_sha
        seen.append(brief)

        return shop_map()

    monkeypatch.setattr(pipeline, "build_change_map", build)

    return seen


@pytest.mark.parametrize(
    "spec",
    [
        "https://github.com/octo-org/my.repo/pull/12",
        "https://github.com/octo-org/my.repo/pull/12/files",
        "https://github.com/octo-org/my.repo/pull/12#discussion_r1",
        "http://www.github.com/octo-org/my.repo/pull/12?w=1",
        "github:octo-org/my.repo#12",
    ],
)
def test_github_pr_urls_resolve_to_the_live_source(spec: str, tmp_path: Path) -> None:
    source, ref = cli._resolve(spec, tmp_path)

    assert isinstance(source, GitHubSource)
    assert ref == PrRef("octo-org", "my.repo", 12)


@pytest.mark.parametrize(
    "spec",
    [
        "https://evil.example/octo-org/repo/pull/12",
        "https://github.com.evil.example/octo-org/repo/pull/12",
        "https://github.com/octo-org/repo/issues/12",
        "https://github.com/octo-org/repo/pull/12x",
        "javascript:alert(1)",
    ],
)
def test_other_urls_are_refused(spec: str, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli._resolve(spec, tmp_path)


def test_map_command_writes_page_and_data(
    built: list[Brief], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def run() -> dict[str, object]:
        argv = ["map", "--source", "fixture:shop", "--store", str(tmp_path / "store")]
        assert cli.main([*argv, "--out", str(tmp_path / "maps")]) == 0
        result: dict[str, object] = json.loads(capsys.readouterr().out)

        return result

    first = run()
    html, data = Path(str(first["html"])), Path(str(first["json"]))

    assert set(first) == {
        "source", "live_verified", "snapshot_id", "html", "json", "symbols", "edges", "steps"
    }  # fmt: skip
    assert (first["source"], first["live_verified"]) == ("fixture", False)
    assert (first["symbols"], first["edges"], first["steps"]) == (7, 12, 10)
    assert (
        html.parent
        == data.parent
        == tmp_path / "maps" / str(first["snapshot_id"]).rsplit(":", 1)[-1][:16]
    )
    assert html.read_text().startswith("<!doctype html>")
    assert json.loads(data.read_text())["url"] is None
    assert built[0].title == "Add discount codes at checkout"

    page, body = html.read_bytes(), data.read_bytes()

    assert run() == first
    assert (html.read_bytes(), data.read_bytes()) == (page, body)


def test_live_sources_link_the_pull_request(
    built: list[Brief],
    make_source: Callable[[str], tuple[FixtureSource, PrRef]],
    clock: FakeClock,
    tmp_path: Path,
) -> None:
    source, ref = make_source("shop")
    source = dataclasses.replace(source, live_verified=True)
    result = pipeline.run_map(source, ref, clock, EligibilityPolicy(), tmp_path)

    assert result.map.url == f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}"
    assert json.loads(result.json.read_text())["url"] == result.map.url

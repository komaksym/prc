from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from prc.fixture_source import FixtureSource
from prc.model import PrRef


def builder() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts/prepare_paired_materials.py"
    spec = importlib.util.spec_from_file_location("paired_materials", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capture_builds_pinned_map_and_original_diff(
    make_source: Callable[[str], tuple[FixtureSource, PrRef]], tmp_path: Path
) -> None:
    source, ref = make_source("shop")
    head = json.loads(source.resources["pr"])["head_sha"]
    out = tmp_path / "packet"
    builder().capture(source, ref, head, out)
    data = json.loads((out / "map.json").read_text())
    assert data["head_sha"] == head
    assert data["url"] == f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}"
    assert (out / "original.diff").read_text().startswith("diff --git")
    record = json.loads((out / "provenance.json").read_text())
    assert record["base_sha"] == data["base_sha"]
    assert record["head_sha"] == head
    assert record["original_diff_sha256"]


def test_capture_refuses_stale_head_without_creating_packet(
    make_source: Callable[[str], tuple[FixtureSource, PrRef]], tmp_path: Path
) -> None:
    source, ref = make_source("shop")
    out = tmp_path / "packet"
    with pytest.raises(ValueError, match="head changed"):
        builder().capture(source, ref, "0" * 40, out)
    assert not out.exists()


def test_capture_never_overwrites_an_existing_packet(
    make_source: Callable[[str], tuple[FixtureSource, PrRef]], tmp_path: Path
) -> None:
    source, ref = make_source("shop")
    head = json.loads(source.resources["pr"])["head_sha"]
    out = tmp_path / "packet"
    out.mkdir()
    (out / "keep").write_text("existing")
    with pytest.raises(FileExistsError):
        builder().capture(source, ref, head, out)
    assert (out / "keep").read_text() == "existing"


def test_lens_page_preserves_ci_comment_and_uses_captured_svg(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "assets").mkdir(parents=True)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><text>CI output</text></svg>'
    name = hashlib.sha256(svg).hexdigest()[:32] + ".svg"
    (source / "assets" / name).write_bytes(svg)
    body = "<!-- pr-lens:sticky --> captured CI explanation"
    (source / "comment.json").write_text(json.dumps({"body": body}))
    (source / "check_run.json").write_text('{"conclusion":"success"}')
    remote = f"https://prlens.dev/api/i/renders/vendor/repo/{name}"
    rendered = f'<details><summary>Drill down</summary><p>CI output</p></details><a href="https://prlens.dev/s/vendor/repo/1">Canvas</a><img src="{remote}">'
    calls = []

    def render(text: str) -> str:
        calls.append(text)
        return rendered

    out = tmp_path / "page"
    builder().lens_page(source, out, render)
    page = (out / "index.html").read_text()
    assert calls == [body]
    assert "<details><summary>Drill down</summary>" in page
    assert 'href="https://prlens.dev/s/vendor/repo/1"' in page
    assert f'src="assets/{name}"' in page
    assert remote not in page
    assert (out / "comment.json").read_bytes() == (source / "comment.json").read_bytes()
    assert (out / "assets" / name).read_bytes() == svg


def test_lens_page_refuses_uncaptured_remote_image(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "assets").mkdir(parents=True)
    (source / "comment.json").write_text('{"body":"CI comment"}')
    with pytest.raises(ValueError, match="uncaptured Lens render"):
        builder().lens_page(
            source,
            tmp_path / "out",
            lambda _: '<img src="https://prlens.dev/api/i/renders/a/b/missing.svg">',
        )
    assert not (tmp_path / "out").exists()


def camo(url: str) -> str:
    return "https://camo.githubusercontent.com/" + "ab" * 32 + "/" + url.encode().hex()


def test_lens_page_resolves_github_camo_proxies_to_captured_light_svg(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "assets").mkdir(parents=True)
    names = []
    for text in ("light", "dark"):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{text}</text></svg>'.encode()
        name = hashlib.sha256(svg).hexdigest()[:32] + ".svg"
        (source / "assets" / name).write_bytes(svg)
        names.append(name)
    (source / "comment.json").write_text('{"body":"CI comment"}')
    light, dark = (f"https://prlens.dev/api/i/renders/vendor/repo/{n}" for n in names)
    cta = "https://prlens.dev/comment/cta/walkthrough-light.svg"
    rendered = (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{camo(dark)}" '
        f'data-canonical-src="{dark}"><img alt="Architecture diagram" src="{camo(light)}" '
        f'data-canonical-src="{light}"></picture>'
        f'<a href="https://prlens.dev/s/vendor/repo/1"><img alt="Open walkthrough" src="{camo(cta)}"></a>'
    )
    out = tmp_path / "page"
    builder().lens_page(source, out, lambda _: rendered)
    page = (out / "index.html").read_text()
    assert f'src="assets/{names[0]}"' in page
    assert "camo.githubusercontent.com" not in page
    assert "prefers-color-scheme: dark" not in page
    assert "<img" in page and page.count("<img") == 1
    assert "Open walkthrough" in page
    assert 'href="https://prlens.dev/s/vendor/repo/1"' in page

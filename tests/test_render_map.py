from __future__ import annotations

import base64
import hashlib
import json
import re
from importlib.resources import files
from pathlib import Path

import pytest

from map_sample import hostile_map, shop_map
from prc.presentation.graphdoc import to_graph_doc
from prc.presentation.render_map import BRAND, data_block, page_data, render_map

ASSETS = files("prc.presentation") / "map_assets"
SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.DOTALL)
EXTERNAL = re.compile(r"""(src|href)\s*=\s*[\"']?(https?:)?//|@import|url\(\s*[\"']?https?:""")


def scripts(html: str) -> tuple[str, str, str]:
    found = SCRIPT.findall(html)
    assert len(found) == 3
    (data_attrs, data), (bundle_attrs, bundle), (player_attrs, player) = found
    assert data_attrs == ' type="application/json" id="map-data"'
    assert bundle_attrs == "" and player_attrs == ""
    return data, bundle, player


def test_render_map_csp_and_data_block() -> None:
    change_map = shop_map()
    html = render_map(change_map)
    data, bundle, player = scripts(html)
    first = base64.b64encode(hashlib.sha256(bundle.encode()).digest()).decode()
    second = base64.b64encode(hashlib.sha256(player.encode()).digest()).decode()
    assert html.startswith("<!doctype html>")
    assert html.count("<script") == 3
    payload = json.loads(data)
    assert sorted(payload) == ["dropped", "graph", "map", "steps"]
    assert payload["graph"] == to_graph_doc(change_map).doc
    assert payload["dropped"] == {"edges": 0, "symbols": 0}
    assert payload["map"]["groups"] == []
    kinds = [(s["kind"], s["via"]) for s in payload["steps"]]
    assert kinds[0] == ("overview", None)
    assert kinds[-1] == ("summary", None)
    assert [k for k, _ in kinds[1:-1]].count("risky_file") == 1
    marker = 'http-equiv="Content-Security-Policy" content="'
    assert marker in html
    assert ("script-src 'sha256-" + first + "' 'sha256-" + second + "'") in html
    assert bundle == (ASSETS / "prlens.bundle.js").read_text()
    assert player == (ASSETS / "map.js").read_text()
    assert not EXTERNAL.search(html)
    assert BRAND in html and "no AI drew this" in html
    for symbol in change_map.symbols:
        assert symbol.id not in html.replace(data, "")


def test_render_map_deterministic_bytes() -> None:
    assert render_map(shop_map()) == render_map(shop_map())


def test_hostile_strings_stay_inert_data() -> None:
    change_map = hostile_map()
    html = render_map(change_map)
    data, bundle, player = scripts(html)
    assert not set(data) & {"<", ">", "&", " ", " "}
    inner = json.loads(data)["map"]["files"][1]["hunks"][0]["lines"][3]["text"]
    assert inner.endswith("bold</b>")
    assert "<img" not in html.replace(data, "").replace(bundle, "")
    assert "alert(" not in html.replace(data, "")
    assert "alert(" not in player


ASSET_BAN = re.compile(
    r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\b|new Function"
)
CALL_BAN = re.compile(r"setTimeout\(\s*['`]|setInterval\(\s*['`]")


def test_assets_never_parse_markup_or_load_resources() -> None:
    for asset in ("map.js", "map.css"):
        text = (ASSETS / asset).read_text()
        assert ASSET_BAN.search(text) is None
        assert CALL_BAN.search(text) is None
        assert re.search(r"\.on[a-z]+\s*=", text) is None
        assert "<script" not in text and "</script" not in text
        assert "@import" not in text
        assert not EXTERNAL.search(text)


def test_script_sets_only_fixed_attribute_names() -> None:
    text = (ASSETS / "map.js").read_text()
    pat = r"setAttribute(?:NS)?\(\s*(?:null,\s*)?([^,)]+)"
    names = re.findall(pat, text)
    assert names
    assert all(re.fullmatch(r'"[a-zA-Z][a-zA-Z-]*"', name) for name in names), names
    assert not [name for name in names if name.startswith('"on')]


def test_page_data_marks_dropped_counts_and_groups() -> None:
    from map_sample import large_map

    plotted = to_graph_doc(large_map(60))
    data = page_data(large_map(60))
    assert data["dropped"] == {"symbols": plotted.dropped_symbols, "edges": plotted.dropped_edges}
    assert [g["id"] for g in data["map"]["groups"]] == ["g0", "g1"]
    assert data_block(shop_map()) == data_block(shop_map())


def test_render_rejects_a_modified_vendor_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prc.presentation import render_map as renderer

    for name in ("prlens.bundle.js", "prlens.lock.json", "map.js", "map.css"):
        (tmp_path / name).write_bytes((ASSETS / name).read_bytes())
    with (tmp_path / "prlens.bundle.js").open("a") as bundle:
        bundle.write("\nconsole.log('tampered');\n")
    monkeypatch.setattr(renderer, "_ASSETS", tmp_path)
    with pytest.raises(ValueError, match="bundle hash"):
        renderer.render_map(shop_map())


def test_conversion_failure_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    from prc.presentation import render_map as renderer

    def fail(_map: object) -> None:
        raise ValueError("node contract failed")

    monkeypatch.setattr(renderer, "to_graph_doc", fail)
    data = renderer.page_data(shop_map())
    assert data["graph"] is None
    assert data["layoutError"] == "node contract failed"
    assert len(data["map"]["files"]) == len(shop_map().files)

from __future__ import annotations

import base64
import hashlib
import json
import re
from importlib.resources import files

import pytest

from map_sample import HOSTILE_LINES, hostile_map, large_map, shop_map
from prc.changemap import ChangeMap
from prc.identity import to_jsonable
from prc.presentation.render_map import BRAND, render_map

ASSETS = files("prc.presentation") / "map_assets"
SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.DOTALL)
EXTERNAL = re.compile(r"""(src|href)\s*=\s*["']?(https?:)?//|@import|url\(\s*["']?https?:""")
SAMPLES = {"shop": shop_map, "hostile": hostile_map, "large": large_map}


def scripts(html: str) -> tuple[str, str]:
    found = SCRIPT.findall(html)

    assert len(found) == 2
    (data_attrs, data), (code_attrs, code) = found

    assert data_attrs == ' type="application/json" id="map-data"' and code_attrs == ""

    return data, code


def stored(change_map: ChangeMap) -> object:
    return json.loads(json.dumps(to_jsonable(change_map)))


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_page_contract(name: str) -> None:
    change_map = SAMPLES[name]()
    html = render_map(change_map)
    data, code = scripts(html)
    digest = base64.b64encode(hashlib.sha256(code.encode()).digest()).decode()

    assert html.startswith("<!doctype html>")
    assert html.count("<script") == 2
    assert json.loads(data) == stored(change_map)
    assert (
        'http-equiv="Content-Security-Policy" content="'
        f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
        "img-src data:; base-uri 'none'; form-action 'none'\"" in html
    )
    assert not EXTERNAL.search(html)
    assert BRAND == "PR map · computed from the code, no AI drew this" and BRAND in html
    assert render_map(change_map) == html


def test_hostile_strings_stay_inert_data() -> None:
    change_map = hostile_map()
    html = render_map(change_map)
    data, code = scripts(html)

    assert not set(data) & {"<", ">", "&", "\u2028", "\u2029"}
    assert json.loads(data)["files"][1]["hunks"][0]["lines"][3]["text"] == HOSTILE_LINES[3]
    assert "<img" not in html and "alert(" not in html.replace(data, "")
    assert "alert(" not in code


ASSET_BAN = re.compile(
    r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\b|new Function"
    r"|setTimeout\(\s*['\"`]|setInterval\(\s*['\"`]|\.on[a-z]+\s*=|<script|</script|@import|url\((?!#)"
)


@pytest.mark.parametrize("asset", ["map.js", "map.css"])
def test_assets_never_parse_markup_or_load_resources(asset: str) -> None:
    text = (ASSETS / asset).read_text()

    assert ASSET_BAN.findall(text) == []
    assert not EXTERNAL.search(text)


def test_script_sets_only_fixed_attribute_names() -> None:
    text = (ASSETS / "map.js").read_text()
    names = re.findall(r"setAttribute(?:NS)?\(\s*(?:null,\s*)?([^,)]+)", text)

    assert names
    assert all(re.fullmatch(r'"[a-zA-Z][a-zA-Z-]*"', name) for name in names), names
    assert not [name for name in names if name.startswith('"on')]

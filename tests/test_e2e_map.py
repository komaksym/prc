from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e" / "maps"

CART = "src/shop/cart.py"
CHECKOUT = f"{CART}::checkout"
LEGACY = f"{CART}::legacy_total"
SUBTOTAL = f"{CART}::Cart.subtotal"
CART_CLASS = f"{CART}::Cart"
DISCOUNT = "src/shop/discounts.py::apply_discount"
TAX = "src/shop/tax.py::compute_tax"
POST = "src/shop/api.py::post_checkout"
PREVIEW = "src/shop/api.py::post_preview"
OLD_TEST = "tests/test_cart.py::test_checkout_adds_tax"
NEW_TEST = "tests/test_cart.py::test_checkout_without_code_keeps_total"
VIEW = "web/src/CartView.tsx::CartView"
FORMAT = "web/src/cart.ts::formatPrice"
TOTAL = "web/src/cart.ts::total"


def map_cli(*args: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "map", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    result: dict[str, Any] = json.loads(completed.stdout)

    return result


def run_fixture(name: str) -> dict[str, Any]:
    out = ARTIFACT / "out"

    return map_cli(
        "--source", f"fixture:{name}", "--store", str(ARTIFACT / "store"), "--out", str(out)
    )


def test_shop_map_is_computed_safe_and_repeatable() -> None:
    shutil.rmtree(ARTIFACT, ignore_errors=True)
    first = run_fixture("shop")

    assert first["source"] == "fixture" and first["live_verified"] is False
    assert (first["symbols"], first["edges"], first["steps"]) == (7, 12, 10)

    html_path, json_path = Path(first["html"]), Path(first["json"])
    html, data = html_path.read_text(), json.loads(json_path.read_text())
    symbols = {s["id"]: s for s in data["symbols"]}

    assert {sid: s["status"] for sid, s in symbols.items()} == {
        CHECKOUT: "modified",
        LEGACY: "deleted",
        DISCOUNT: "added",
        TAX: "modified",
        NEW_TEST: "added",
        VIEW: "modified",
        FORMAT: "added",
        CART_CLASS: "context",
        SUBTOTAL: "context",
        POST: "context",
        PREVIEW: "context",
        OLD_TEST: "context",
        TOTAL: "context",
    }
    assert {
        sid: (s["added"], s["removed"]) for sid, s in symbols.items() if s["status"] != "context"
    } == {
        CHECKOUT: (2, 2),
        LEGACY: (0, 2),
        DISCOUNT: (4, 0),
        TAX: (2, 1),
        NEW_TEST: (2, 0),
        VIEW: (1, 1),
        FORMAT: (3, 0),
    }
    assert (symbols[CHECKOUT]["span"], symbols[CHECKOUT]["base_span"]) == ([13, 15], [16, 18])
    assert (symbols[LEGACY]["span"], symbols[LEGACY]["base_span"]) == (None, [12, 13])
    assert (symbols[CHECKOUT]["call_sites"], symbols[CART_CLASS]["call_sites"]) == (4, 4)
    assert symbols[SUBTOTAL]["kind"] == "method" and symbols[CART_CLASS]["kind"] == "class"

    checkout_lines = [
        (line["op"], line["text"]) for hunk in symbols[CHECKOUT]["hunks"] for line in hunk["lines"]
    ]

    assert ("-", "    total = legacy_total(cart)") in checkout_lines
    assert ("+", "    total = apply_discount(cart.subtotal(), code)") in checkout_lines

    assert {(e["source"], e["target"], e["status"], e["resolution"]) for e in data["edges"]} == {
        (CHECKOUT, DISCOUNT, "added", "exact"),
        (CHECKOUT, LEGACY, "removed", "exact"),
        (CHECKOUT, TAX, "kept", "exact"),
        (CHECKOUT, SUBTOTAL, "added", "name"),
        (LEGACY, SUBTOTAL, "removed", "name"),
        (POST, CHECKOUT, "kept", "exact"),
        (PREVIEW, CHECKOUT, "kept", "exact"),
        (OLD_TEST, CHECKOUT, "kept", "exact"),
        (NEW_TEST, CHECKOUT, "added", "exact"),
        (NEW_TEST, CART_CLASS, "added", "exact"),
        (VIEW, FORMAT, "added", "exact"),
        (VIEW, TOTAL, "kept", "exact"),
    }

    assert {
        f["path"]: (f["kind"], f["status"], f["language"], f["sensitive"]) for f in data["files"]
    } == {
        ".github/workflows/ci.yml": ("config", "modified", None, "CI workflow"),
        "README.md": ("docs", "modified", None, None),
        CART: ("code", "modified", "python", None),
        "src/shop/discounts.py": ("code", "added", "python", None),
        "src/shop/tax.py": ("code", "modified", "python", None),
        "tests/test_cart.py": ("test", "modified", "python", None),
        "web/src/CartView.tsx": ("code", "modified", "tsx", None),
        "web/src/cart.ts": ("code", "modified", "typescript", None),
    }

    assert [(s["kind"], s["focus"], s["via"]) for s in data["tour"]] == [
        ("overview", [], None),
        ("risky_file", [".github/workflows/ci.yml"], None),
        ("entry", [CHECKOUT], None),
        ("callee", [DISCOUNT], CHECKOUT),
        ("callee", [TAX], CHECKOUT),
        ("callee", [LEGACY], CHECKOUT),
        ("entry", [VIEW], None),
        ("callee", [FORMAT], VIEW),
        ("test", [NEW_TEST], None),
        ("summary", [], None),
    ]

    assert html.startswith("<!doctype html>")

    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", html, re.DOTALL)
    executable = [body for attrs, body in scripts if "application/json" not in attrs]
    blocks = [body for attrs, body in scripts if 'id="map-data"' in attrs]

    assert len(scripts) == 2 and len(executable) == 1 and len(blocks) == 1
    assert json.loads(blocks[0]) == data

    digest = base64.b64encode(hashlib.sha256(executable[0].encode()).digest()).decode()
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)

    assert csp is not None
    assert "default-src 'none'" in csp[1] and f"'sha256-{digest}'" in csp[1]
    assert not re.search(
        r"""(src|href)\s*=\s*["']?(https?:)?//|@import|url\(\s*["']?https?:""", html
    )

    second = run_fixture("shop")

    assert second["html"] == first["html"]
    assert Path(second["html"]).read_text() == html
    assert Path(second["json"]).read_text() == json_path.read_text()


def test_hostile_map_renders_inert() -> None:
    result = run_fixture("hostile")
    html = Path(result["html"]).read_text()

    assert html.count("<script") == 2
    assert "<img" not in html
    assert "</text><script>" not in html

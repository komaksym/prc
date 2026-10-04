from __future__ import annotations

from pathlib import Path

from prc.brief import build_brief
from prc.capture import capture_bundle
from prc.changemap import ChangeMap, Symbol, build_change_map
from prc.fixture_source import FixtureSource, build_source
from prc.gitutil import list_paths
from prc.model import PrRef
from prc.scenarios import FILE, SCENARIOS
from prc.snapshot import build_snapshot
from prc.verification import EligibilityPolicy

from conftest import FakeClock

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


def map_of(source: FixtureSource, ref: PrRef) -> ChangeMap:
    repo = source.repo_path(ref)
    bundle = capture_bundle(source, ref, FakeClock())
    acquisition = build_snapshot(bundle, source.label, False, repo, EligibilityPolicy())
    comparison = acquisition.snapshot.comparison
    known = frozenset(list_paths(repo, comparison.merge_base_sha)) | frozenset(
        list_paths(repo, comparison.head_sha)
    )

    return build_change_map(acquisition, repo, build_brief(acquisition, known))


def fixture_map(tmp_path: Path, name: str) -> ChangeMap:
    return map_of(*SCENARIOS[name](tmp_path))


def custom_map(tmp_path: Path, base: dict[str, bytes], head: dict[str, bytes]) -> ChangeMap:
    meta: dict[str, object] = {
        "title": "Custom",
        "body": "",
        "author": "someone",
        "labels": [],
        "draft": False,
        "agent_authored": False,
    }
    source, ref = build_source(
        tmp_path / "custom.git",
        {path: (FILE, data) for path, data in base.items()},
        {path: (FILE, data) for path, data in head.items()},
        meta,
        lambda *_: [],
        {},
        None,
    )

    return map_of(source, ref)


def by_id(change: ChangeMap) -> dict[str, Symbol]:
    return {symbol.id: symbol for symbol in change.symbols}


def test_shop_map_matches_the_e2e_contract(tmp_path: Path) -> None:
    change = fixture_map(tmp_path, "shop")
    symbols = by_id(change)

    assert (change.pr, change.url, change.title, change.author) == (
        "fixture-org/demo#1",
        None,
        "Add discount codes at checkout",
        "coding-agent[bot]",
    )
    assert {sid: s.status for sid, s in symbols.items()} == {
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
    assert {sid: (s.added, s.removed) for sid, s in symbols.items() if s.status != "context"} == {
        CHECKOUT: (2, 2),
        LEGACY: (0, 2),
        DISCOUNT: (4, 0),
        TAX: (2, 1),
        NEW_TEST: (2, 0),
        VIEW: (1, 1),
        FORMAT: (3, 0),
    }
    assert (symbols[CHECKOUT].span, symbols[CHECKOUT].base_span) == ((13, 15), (16, 18))
    assert (symbols[LEGACY].span, symbols[LEGACY].base_span) == (None, (12, 13))
    assert (symbols[CHECKOUT].call_sites, symbols[CART_CLASS].call_sites) == (4, 4)
    assert symbols[SUBTOTAL].kind == "method" and symbols[CART_CLASS].kind == "class"

    checkout_lines = [
        (line.op, line.text) for hunk in symbols[CHECKOUT].hunks for line in hunk.lines
    ]

    assert ("-", "    total = legacy_total(cart)") in checkout_lines
    assert ("+", "    total = apply_discount(cart.subtotal(), code)") in checkout_lines
    assert all(
        line.op != "+" or line.new in range(13, 16)
        for hunk in symbols[CHECKOUT].hunks
        for line in hunk.lines
    )

    assert {(e.source, e.target, e.status, e.resolution) for e in change.edges} == {
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
    assert {f.path: (f.kind, f.status, f.language, f.sensitive) for f in change.files} == {
        ".github/workflows/ci.yml": ("config", "modified", None, "CI workflow"),
        "README.md": ("docs", "modified", None, None),
        CART: ("code", "modified", "python", None),
        "src/shop/discounts.py": ("code", "added", "python", None),
        "src/shop/tax.py": ("code", "modified", "python", None),
        "tests/test_cart.py": ("test", "modified", "python", None),
        "web/src/CartView.tsx": ("code", "modified", "tsx", None),
        "web/src/cart.ts": ("code", "modified", "typescript", None),
    }
    assert [(s.kind, s.focus, s.via) for s in change.tour] == [
        ("overview", (), None),
        ("risky_file", (".github/workflows/ci.yml",), None),
        ("entry", (CHECKOUT,), None),
        ("callee", (DISCOUNT,), CHECKOUT),
        ("callee", (TAX,), CHECKOUT),
        ("callee", (LEGACY,), CHECKOUT),
        ("entry", (VIEW,), None),
        ("callee", (FORMAT,), VIEW),
        ("test", (NEW_TEST,), None),
        ("summary", (), None),
    ]


def test_shop_map_is_sorted_and_repeatable(tmp_path: Path) -> None:
    first = fixture_map(tmp_path / "a", "shop")
    second = fixture_map(tmp_path / "b", "shop")

    assert first == second
    assert [s.id for s in first.symbols] == sorted(s.id for s in first.symbols)
    assert [(e.source, e.target) for e in first.edges] == sorted(
        (e.source, e.target) for e in first.edges
    )
    assert [f.path for f in first.files] == sorted(f.path for f in first.files)

    files = {f.path: f for f in first.files}

    assert files[CART].symbols == (CART_CLASS, SUBTOTAL, CHECKOUT, LEGACY)
    assert files["README.md"].symbols == ()
    assert (files[CART].added, files[CART].removed) == (3, 6)
    assert files[CART].hunks and files["README.md"].hunks
    assert first.base_sha != first.head_sha


def test_added_and_deleted_files(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"gone.py": b"def old():\n    return 1\n"},
        {"fresh.ts": b"export function made(): number {\n  return 2;\n}\n"},
    )
    symbols = by_id(change)
    files = {f.path: (f.status, f.language) for f in change.files}

    assert files == {"gone.py": ("deleted", "python"), "fresh.ts": ("added", "typescript")}
    assert (symbols["gone.py::old"].status, symbols["gone.py::old"].span) == ("deleted", None)
    assert symbols["gone.py::old"].base_span == (1, 2)
    assert (symbols["fresh.ts::made"].status, symbols["fresh.ts::made"].base_span) == (
        "added",
        None,
    )
    assert (symbols["fresh.ts::made"].added, symbols["fresh.ts::made"].removed) == (3, 0)


def test_non_utf8_bytes_and_crlf_keep_line_attribution(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {
            "latin.py": b"# caf\xe9\ndef f():\n    return 1\n",
            "dos.py": b"def g():\r\n    return 1\r\n\r\n\r\ndef h():\r\n    return 2\r\n",
        },
        {
            "latin.py": b"# caf\xe9\ndef f():\n    return 2\n",
            "dos.py": b"def g():\r\n    return 1\r\n\r\n\r\ndef h():\r\n    return 3\r\n",
        },
    )
    symbols = by_id(change)

    assert {sid: s.status for sid, s in symbols.items()} == {
        "latin.py::f": "modified",
        "dos.py::h": "modified",
    }
    assert symbols["latin.py::f"].span == (2, 3)
    assert symbols["dos.py::h"].span == (5, 6)
    assert [
        (line.op, line.text)
        for hunk in symbols["dos.py::h"].hunks
        for line in hunk.lines
        if line.op != " "
    ] == [
        ("-", "    return 2"),
        ("+", "    return 3"),
    ]


def test_hunk_spanning_two_symbols_splits_its_lines(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"two.py": b"def a():\n    return 1\n\n\ndef b():\n    return 2\n"},
        {"two.py": b"def a():\n    return 10\n\n\ndef b():\n    return 20\n"},
    )
    symbols = by_id(change)
    file = change.files[0]

    assert len(file.hunks) == 1
    assert {sid: (s.status, s.added, s.removed) for sid, s in symbols.items()} == {
        "two.py::a": ("modified", 1, 1),
        "two.py::b": ("modified", 1, 1),
    }
    assert [
        line.text for hunk in symbols["two.py::b"].hunks for line in hunk.lines if line.op != " "
    ] == [
        "    return 2",
        "    return 20",
    ]


def test_import_only_change_stays_on_the_file(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"mod.py": b"import os\n\n\ndef f():\n    return os.sep\n"},
        {"mod.py": b"import os\nimport sys\n\n\ndef f():\n    return os.sep\n"},
    )

    assert change.symbols == () and change.edges == ()
    assert (change.files[0].added, change.files[0].removed, change.files[0].symbols) == (1, 0, ())
    assert [(s.kind, s.focus) for s in change.tour] == [("overview", ()), ("summary", ())]


def test_unsupported_extension_and_generated_files_are_not_parsed(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"main.go": b"package main\nfunc f() {}\n", "dist/bundle.js": b"function f() {}\n"},
        {
            "main.go": b"package main\nfunc f() { g() }\n",
            "dist/bundle.js": b"function f() { g() }\n",
        },
    )

    assert {f.path: (f.kind, f.language) for f in change.files} == {
        "main.go": ("code", None),
        "dist/bundle.js": ("generated", None),
    }
    assert change.symbols == ()


def test_unchanged_callers_are_capped_at_six_by_file_then_line(tmp_path: Path) -> None:
    callers = b"from lib import target\n" + b"".join(
        b"\n\ndef c%d():\n    target()\n" % n for n in range(8)
    )
    change = custom_map(
        tmp_path,
        {"lib.py": b"def target():\n    return 1\n", "callers.py": callers},
        {"lib.py": b"def target():\n    return 2\n", "callers.py": callers},
    )
    symbols = by_id(change)

    assert sorted(sid for sid, s in symbols.items() if s.status == "context") == [
        f"callers.py::c{n}" for n in range(6)
    ]
    assert symbols["lib.py::target"].call_sites == 8
    assert len(change.edges) == 6


def test_hostile_and_opaque_fixtures_do_not_crash_or_parse_opaque_files(tmp_path: Path) -> None:
    hostile = fixture_map(tmp_path, "hostile")
    opaque = fixture_map(tmp_path, "opaque")
    opaque_paths = {f.path for f in opaque.files if f.kind == "opaque"}

    assert {f.path for f in hostile.files} >= {"src/app.py", "src/<script>alert(1)</script>.py"}
    assert hostile.symbols == ()
    assert opaque_paths >= {"src/big.py", "assets/old.png", "assets/model.bin", "vendor/lib"}
    assert all(
        f.language is None and f.symbols == () for f in opaque.files if f.path in opaque_paths
    )
    assert all(s.path not in opaque_paths for s in opaque.symbols)
    assert [s.kind for s in opaque.tour] == ["overview", "summary"]


def test_tour_orders_entries_by_size_and_removed_calls_last_without_self_loops(
    tmp_path: Path,
) -> None:
    change = custom_map(
        tmp_path,
        {
            "a.py": b"def zeta():\n    old_helper()\n    keep()\n\n\n"
            b"def old_helper():\n    return 1\n\n\n"
            b"def keep():\n    return 1\n\n\n"
            b"def alpha():\n    return alpha()\n"
        },
        {
            "a.py": b"def zeta():\n    keep()\n    new_helper()\n    x = 1\n    return x\n\n\n"
            b"def keep():\n    return 2\n\n\n"
            b"def new_helper():\n    return 1\n\n\n"
            b"def alpha():\n    return alpha() + 1\n"
        },
    )

    assert all(edge.source != edge.target for edge in change.edges)
    assert [(s.kind, s.focus, s.via) for s in change.tour] == [
        ("overview", (), None),
        ("entry", ("a.py::zeta",), None),
        ("callee", ("a.py::keep",), "a.py::zeta"),
        ("callee", ("a.py::new_helper",), "a.py::zeta"),
        ("callee", ("a.py::old_helper",), "a.py::zeta"),
        ("entry", ("a.py::alpha",), None),
        ("summary", (), None),
    ]


def test_missing_final_newline_never_glues_lines_or_counts_the_marker(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"tail.py": b"def f():\n    return 1"},
        {"tail.py": b"def f():\n    return 2\n"},
    )
    symbol = by_id(change)["tail.py::f"]

    assert (change.files[0].added, change.files[0].removed) == (1, 1)
    assert (symbol.added, symbol.removed) == (1, 1)
    assert [(line.op, line.text) for hunk in symbol.hunks for line in hunk.lines] == [
        (" ", "def f():"),
        ("-", "    return 1"),
        ("+", "    return 2"),
    ]


def test_kept_callee_is_context_only_when_its_call_line_changed(tmp_path: Path) -> None:
    base = b"def helper():\n    return 1\n\n\ndef other(n):\n    return n\n\n\n"
    change = custom_map(
        tmp_path,
        {"a.py": base + b"def f():\n    x = helper()\n    y = other(1)\n    return x + other(y)\n"},
        {"a.py": base + b"def f():\n    x = helper()\n    y = other(1)\n    return x - other(y)\n"},
    )

    assert {sid: s.status for sid, s in by_id(change).items()} == {
        "a.py::f": "modified",
        "a.py::other": "context",
    }
    assert {(e.source, e.target, e.status) for e in change.edges} == {
        ("a.py::f", "a.py::other", "kept")
    }


def test_callees_are_capped_by_edge_status_before_file_and_line(tmp_path: Path) -> None:
    helpers = b"".join(
        b"def %s(*args):\n    return 1\n\n\n" % name
        for name in (b"t1", b"t2", b"r1", b"r2", b"a1", b"a2", b"a3", b"k1")
    )
    change = custom_map(
        tmp_path,
        {
            "h.py": helpers,
            "hub.py": b"from h import *\n\n\ndef hub():\n"
            b"    t1(0)\n    t2(0)\n    k1()\n    r1()\n    r2()\n",
        },
        {
            "h.py": helpers,
            "hub.py": b"from h import *\n\n\ndef hub():\n"
            b"    t1(1)\n    t2(1)\n    k1()\n    a1()\n    a2()\n    a3()\n",
        },
    )

    assert {(e.target, e.status) for e in change.edges} == {
        ("h.py::a1", "added"),
        ("h.py::a2", "added"),
        ("h.py::a3", "added"),
        ("h.py::r1", "removed"),
        ("h.py::r2", "removed"),
        ("h.py::t1", "kept"),
    }
    assert {s.id for s in change.symbols} == {"hub.py::hub"} | {e.target for e in change.edges}

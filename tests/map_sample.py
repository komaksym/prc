"""Hand-built change maps for presentation tests while the domain builder is in flight."""

from __future__ import annotations

from prc.brief import Brief, Check, FileChange, Kind
from prc.changemap import (
    ChangeMap,
    DiffLine,
    Edge,
    EdgeStatus,
    FileNode,
    FileStatus,
    Hunk,
    Language,
    Step,
    Symbol,
    SymbolKind,
    SymbolStatus,
)

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
CI = ".github/workflows/ci.yml"


def _plus(start: int, *texts: str) -> tuple[DiffLine, ...]:
    return tuple(DiffLine("+", None, start + i, text) for i, text in enumerate(texts))


def _minus(start: int, *texts: str) -> tuple[DiffLine, ...]:
    return tuple(DiffLine("-", start + i, None, text) for i, text in enumerate(texts))


def _symbol(
    sid: str,
    kind: SymbolKind,
    status: SymbolStatus,
    span: tuple[int, int] | None,
    base_span: tuple[int, int] | None,
    hunks: tuple[Hunk, ...] = (),
    call_sites: int = 0,
) -> Symbol:
    path, qualname = sid.split("::", 1)
    added = sum(line.op == "+" for hunk in hunks for line in hunk.lines)
    removed = sum(line.op == "-" for hunk in hunks for line in hunk.lines)

    return Symbol(
        sid, path, qualname, kind, status, span, base_span, added, removed, hunks, call_sites
    )


def _file(
    path: str,
    kind: Kind,
    status: FileStatus,
    language: Language | None,
    hunks: tuple[Hunk, ...],
    symbols: tuple[str, ...] = (),
    sensitive: str | None = None,
) -> FileNode:
    added = sum(line.op == "+" for hunk in hunks for line in hunk.lines)
    removed = sum(line.op == "-" for hunk in hunks for line in hunk.lines)

    return FileNode(path, kind, status, language, sensitive, added, removed, hunks, symbols)


CHECKOUT_HUNK = Hunk(
    16,
    13,
    _minus(16, "def checkout(cart, region):", "    total = legacy_total(cart)")
    + _plus(13, "def checkout(cart, region, code=None):")
    + _plus(14, "    total = apply_discount(cart.subtotal(), code)")
    + (DiffLine(" ", 18, 15, "    return total + compute_tax(total, region)"),),
)
LEGACY_HUNK = Hunk(
    12, 12, _minus(12, "def legacy_total(cart):", "    return cart.subtotal() * 1.0")
)
DISCOUNT_HUNK = Hunk(
    0,
    1,
    _plus(
        1,
        "def apply_discount(amount, code):",
        '    if code == "WELCOME10":',
        "        return amount * 0.9",
        "    return amount",
    ),
)
TAX_HUNK = Hunk(
    4,
    4,
    (DiffLine(" ", 4, 4, "def compute_tax(amount, region):"),)
    + _minus(5, "    return amount * RATES.get(region, 0.0)")
    + _plus(5, "    rate = RATES.get(region, 0.0)", "    return round(amount * rate, 2)"),
)
TEST_HUNK = Hunk(
    5,
    8,
    _plus(
        8,
        "def test_checkout_without_code_keeps_total():",
        '    assert checkout(Cart([]), "us", None) == 0',
    ),
)
VIEW_HUNK = Hunk(
    4,
    4,
    _minus(4, '  return <div className="cart">Total: {total(prices)}</div>;')
    + _plus(4, '  return <div className="cart">Total: {formatPrice(total(prices))}</div>;'),
)
FORMAT_HUNK = Hunk(
    3,
    4,
    _plus(
        5,
        "export function formatPrice(cents: number): string {",
        "  return `$${(cents / 100).toFixed(2)}`;",
        "}",
    ),
)


def shop_brief(files: tuple[FileNode, ...], title: str = "Add discount codes at checkout") -> Brief:
    return Brief(
        "acme/shop#7",
        title,
        "f" * 40,
        tuple(
            FileChange(f.path, f.kind, f.added, f.removed, f.path != CI, f.sensitive) for f in files
        ),
        (Check("unit-tests", "passed"),),
        (),
        (),
    )


def shop_map() -> ChangeMap:
    """Mirrors the `shop` fixture's expected map in tests/test_e2e_map.py."""

    symbols = (
        _symbol(CART_CLASS, "class", "context", (5, 10), (4, 9), call_sites=4),
        _symbol(SUBTOTAL, "method", "context", (9, 10), (8, 9), call_sites=1),
        _symbol(CHECKOUT, "function", "modified", (13, 15), (16, 18), (CHECKOUT_HUNK,), 4),
        _symbol(LEGACY, "function", "deleted", None, (12, 13), (LEGACY_HUNK,)),
        _symbol(DISCOUNT, "function", "added", (1, 4), None, (DISCOUNT_HUNK,), 1),
        _symbol(POST, "function", "context", (4, 6), (4, 6)),
        _symbol(PREVIEW, "function", "context", (9, 10), (9, 10)),
        _symbol(TAX, "function", "modified", (4, 6), (4, 5), (TAX_HUNK,), 1),
        _symbol(OLD_TEST, "function", "context", (4, 5), (4, 5)),
        _symbol(NEW_TEST, "function", "added", (8, 9), None, (TEST_HUNK,)),
        _symbol(VIEW, "function", "modified", (3, 5), (3, 5), (VIEW_HUNK,)),
        _symbol(FORMAT, "function", "added", (5, 7), None, (FORMAT_HUNK,), 1),
        _symbol(TOTAL, "function", "context", (1, 3), (1, 3), call_sites=1),
    )
    files = (
        _file(
            CI,
            "config",
            "modified",
            None,
            (
                Hunk(
                    7,
                    7,
                    (DiffLine(" ", 7, 7, "      - run: pytest"),)
                    + _plus(8, "        continue-on-error: true"),
                ),
            ),
            sensitive="CI workflow",
        ),
        _file(
            "README.md",
            "docs",
            "modified",
            None,
            (Hunk(1, 1, _plus(2, "", "Checkout accepts a discount code.")),),
        ),
        _file(
            CART,
            "code",
            "modified",
            "python",
            (
                Hunk(1, 1, _plus(1, "from shop.discounts import apply_discount")),
                LEGACY_HUNK,
                CHECKOUT_HUNK,
            ),
            (CHECKOUT, LEGACY),
        ),
        _file("src/shop/discounts.py", "code", "added", "python", (DISCOUNT_HUNK,), (DISCOUNT,)),
        _file("src/shop/tax.py", "code", "modified", "python", (TAX_HUNK,), (TAX,)),
        _file("tests/test_cart.py", "test", "modified", "python", (TEST_HUNK,), (NEW_TEST,)),
        _file(
            "web/src/CartView.tsx",
            "code",
            "modified",
            "tsx",
            (
                Hunk(
                    1,
                    1,
                    _minus(1, 'import { total } from "./cart";')
                    + _plus(1, 'import { formatPrice, total } from "./cart";'),
                ),
                VIEW_HUNK,
            ),
            (VIEW,),
        ),
        _file("web/src/cart.ts", "code", "modified", "typescript", (FORMAT_HUNK,), (FORMAT,)),
    )
    edges = (
        Edge(CHECKOUT, SUBTOTAL, "added", "name"),
        Edge(CHECKOUT, DISCOUNT, "added", "exact"),
        Edge(CHECKOUT, LEGACY, "removed", "exact"),
        Edge(CHECKOUT, TAX, "kept", "exact"),
        Edge(LEGACY, SUBTOTAL, "removed", "name"),
        Edge(POST, CHECKOUT, "kept", "exact"),
        Edge(PREVIEW, CHECKOUT, "kept", "exact"),
        Edge(OLD_TEST, CHECKOUT, "kept", "exact"),
        Edge(NEW_TEST, CART_CLASS, "added", "exact"),
        Edge(NEW_TEST, CHECKOUT, "added", "exact"),
        Edge(VIEW, FORMAT, "added", "exact"),
        Edge(VIEW, TOTAL, "kept", "exact"),
    )
    tour = (
        Step("overview", (), None),
        Step("risky_file", (CI,), None),
        Step("entry", (CHECKOUT,), None),
        Step("callee", (DISCOUNT,), CHECKOUT),
        Step("callee", (TAX,), CHECKOUT),
        Step("callee", (LEGACY,), CHECKOUT),
        Step("entry", (VIEW,), None),
        Step("callee", (FORMAT,), VIEW),
        Step("test", (NEW_TEST,), None),
        Step("summary", (), None),
    )

    return ChangeMap(
        "acme/shop#7",
        None,
        "Add discount codes at checkout",
        "coding-agent[bot]",
        "a" * 40,
        "f" * 40,
        shop_brief(files),
        files,
        symbols,
        edges,
        tour,
    )


HOSTILE_PATH = "src/<script>alert(1)</script>.py"
HOSTILE_DOC = 'docs/"onmouseover="alert(2).md'
HOSTILE_LINES = (
    "</script><script>alert(3)</script>",
    "<img src=x onerror=alert(4)>",
    "javascript:alert(5)",
    "a\u2028b\u2029c & <b>bold</b>",
)


def hostile_map() -> ChangeMap:
    """PR-controlled strings in every slot the page renders."""

    evil = f"{HOSTILE_PATH}::<img src=x onerror=alert(6)>"
    caller = f"{HOSTILE_PATH}::javascript:alert(7)"
    hunk = Hunk(1, 1, _plus(1, *HOSTILE_LINES))
    symbols = (
        _symbol(caller, "function", "context", (9, 10), (9, 10), call_sites=1),
        _symbol(evil, "function", "added", (1, 4), None, (hunk,), 1),
    )
    files = (
        _file(HOSTILE_DOC, "docs", "added", None, (hunk,)),
        _file(HOSTILE_PATH, "code", "added", "python", (hunk,), (evil,), "<svg onload=alert(8)>"),
    )
    title = "</script><img src=x onerror=alert(9)> javascript:alert(10)"

    return ChangeMap(
        "evil/<script>#1",
        None,
        title,
        '"><img src=x onerror=alert(11)>',
        "a" * 40,
        "b" * 40,
        Brief(
            "evil/<script>#1",
            title,
            "b" * 40,
            tuple(
                FileChange(f.path, f.kind, f.added, f.removed, False, f.sensitive) for f in files
            ),
            (Check("<img src=x onerror=alert(12)>", "failed"),),
            (),
            (),
        ),
        files,
        symbols,
        (Edge(caller, evil, "added", "name"),),
        (
            Step("overview", (), None),
            Step("risky_file", (HOSTILE_PATH,), None),
            Step("entry", (evil,), None),
            Step("summary", (), None),
        ),
    )


def large_map(changed: int = 60) -> ChangeMap:
    """A synthetic PR touching `changed` symbols in layered call chains, for scale checks."""

    def sid(i: int) -> str:
        return f"src/pkg/mod{i % 12:02d}.py::func_{i:03d}"

    symbols: list[Symbol] = []
    edges: list[Edge] = []
    statuses: tuple[SymbolStatus, ...] = ("modified", "added", "modified", "deleted", "modified")

    for i in range(changed):
        status = statuses[i % len(statuses)]
        hunk = Hunk(
            10 * i + 1,
            10 * i + 1,
            _minus(10 * i + 1, f"    old_{i}()") + _plus(10 * i + 1, f"    new_{i}()", "    pass"),
        )
        span = None if status == "deleted" else (10 * i, 10 * i + 3)
        base = None if status == "added" else (10 * i, 10 * i + 2)
        symbols.append(_symbol(sid(i), "function", status, span, base, (hunk,), i % 7))

        if i >= 6:
            source_status = statuses[(i // 3) % len(statuses)]
            gone = "deleted" in (status, source_status)
            edge_status: EdgeStatus = "removed" if gone else ("added", "kept")[i % 2]
            edges.append(Edge(sid(i // 3), sid(i), edge_status, ("exact", "name")[i % 5 == 0]))

    for j in range(12):
        caller = f"src/app/routes{j % 4}.py::handler_{j:02d}"
        callee = f"src/lib/util{j % 3}.py::helper_{j:02d}"
        symbols.append(_symbol(caller, "function", "context", (j, j + 2), (j, j + 2)))
        symbols.append(_symbol(callee, "function", "context", (j, j + 2), (j, j + 2), call_sites=9))
        edges.append(Edge(caller, sid(j * 5 % 6), "kept", "exact"))
        edges.append(Edge(sid(changed - 1 - j * 4), callee, ("kept", "added")[j % 2], "exact"))

    for k in range(8):
        test = f"tests/test_mod{k:02d}.py::test_case_{k}"
        symbols.append(
            _symbol(
                test, "function", "added", (1, 3), None, (Hunk(0, 1, _plus(1, "def t(): pass")),)
            )
        )
        edges.append(Edge(test, sid(k * 7), "added", "exact"))

    by_file: dict[str, list[str]] = {}

    for symbol in symbols:
        if symbol.status != "context":
            by_file.setdefault(symbol.path, []).append(symbol.id)

    files = tuple(
        _file(
            path,
            "test" if path.startswith("tests/") else "code",
            "modified",
            "python",
            (),
            tuple(sorted(ids)),
        )
        for path, ids in sorted(by_file.items())
    ) + (
        _file(CI, "config", "modified", None, (), sensitive="CI workflow"),
        _file("pyproject.toml", "config", "modified", None, (), sensitive="dependency manifest"),
        _file("docs/guide.md", "docs", "modified", None, ()),
    )
    ordered = tuple(sorted(symbols, key=lambda s: s.id))
    changed_ids = sorted(
        s.id for s in ordered if s.status != "context" and not s.path.startswith("tests/")
    )
    tour = (
        (Step("overview", (), None), Step("risky_file", (CI,), None))
        + tuple(Step("entry", (i,), None) for i in changed_ids)
        + (Step("summary", (), None),)
    )

    return ChangeMap(
        "acme/big#99",
        "https://github.com/acme/big/pull/99",
        "Refactor the pipeline into staged modules",
        "coding-agent[bot]",
        "a" * 40,
        "b" * 40,
        shop_brief(files, "Refactor the pipeline into staged modules"),
        files,
        ordered,
        tuple(sorted(edges, key=lambda e: (e.source, e.target))),
        tour,
    )

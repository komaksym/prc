from __future__ import annotations

import pytest

from prc.codegraph import MAX_PARSE_BYTES, Index, ParsedFile, language_of, parse_file


def parse(path: str, text: str | bytes) -> ParsedFile:
    parsed = parse_file(path, text.encode() if isinstance(text, str) else text)

    assert parsed is not None

    return parsed


def defs(path: str, text: str | bytes) -> set[tuple[str, str, tuple[int, int]]]:
    return {(d.qualname, d.kind, d.span) for d in parse(path, text).definitions}


def edges(files: dict[str, str]) -> set[tuple[str, str, str]]:
    index = Index({path: parse(path, text) for path, text in files.items()})

    return {
        (f"{call.path}::{call.scope}", call.target, call.resolution) for call in index.resolve_all()
    }


@pytest.mark.parametrize(
    ("path", "language"),
    [
        ("a.py", "python"),
        ("a.pyi", "python"),
        ("a.js", "javascript"),
        ("a.jsx", "javascript"),
        ("a.mjs", "javascript"),
        ("a.cjs", "javascript"),
        ("a.ts", "typescript"),
        ("a.mts", "typescript"),
        ("a.cts", "typescript"),
        ("a.tsx", "tsx"),
        ("a.go", None),
        ("Makefile", None),
        ("a.py.txt", None),
    ],
)
def test_registry_maps_extensions_to_languages(path: str, language: str | None) -> None:
    assert language_of(path) == language


def test_mjs_and_jsx_files_parse_with_the_javascript_grammar() -> None:
    assert defs("a.mjs", "export function f() {}\n") == {("f", "function", (1, 1))}
    assert parse("a.jsx", "export const App = () => <div>{f()}</div>;\n").calls[0].scope == "App"


def test_oversize_binary_and_unsupported_files_are_not_parsed() -> None:
    assert parse_file("big.py", b"x = 1\n" * (MAX_PARSE_BYTES // 6 + 1)) is None
    assert parse_file("nul.py", b"def f():\x00\n") is None
    assert parse_file("main.go", b"package main\n") is None


def test_nested_functions_get_dotted_qualnames_and_scoped_resolution() -> None:
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        helper()\n"
        "    return inner()\n"
        "\n"
        "def helper():\n"
        "    inner()\n"
    )

    assert defs("m.py", source) == {
        ("outer", "function", (1, 4)),
        ("outer.inner", "function", (2, 3)),
        ("helper", "function", (6, 7)),
    }
    assert edges({"m.py": source}) == {
        ("m.py::outer.inner", "m.py::helper", "exact"),
        ("m.py::outer", "m.py::outer.inner", "exact"),
    }


def test_decorated_function_span_and_decorator_call_belong_to_the_function() -> None:
    source = "def deco(n):\n    return n\n\n\n@deco(1)\n@other\ndef wrapped():\n    pass\n"

    assert ("wrapped", "function", (5, 8)) in defs("m.py", source)
    assert edges({"m.py": source}) == {("m.py::wrapped", "m.py::deco", "exact")}


def test_method_and_function_with_the_same_name() -> None:
    source = (
        "def run():\n    pass\n\n"
        "class Job:\n"
        "    def run(self):\n        run()\n        self.run()\n\n"
        "def go(job):\n    job.run()\n"
    )

    assert {(q, k) for q, k, _ in defs("m.py", source)} == {
        ("run", "function"),
        ("Job", "class"),
        ("Job.run", "method"),
        ("go", "function"),
    }
    assert edges({"m.py": source}) == {
        ("m.py::Job.run", "m.py::run", "exact"),
        ("m.py::Job.run", "m.py::Job.run", "exact"),
    }


def test_self_and_this_resolve_to_the_enclosing_class() -> None:
    python = "class A:\n    def a(self):\n        self.b()\n\n    def b(self):\n        pass\n"
    script = "class K {\n  a() { this.b(); }\n  b = () => 1;\n}\n"

    assert edges({"m.py": python, "k.js": script}) == {
        ("m.py::A.a", "m.py::A.b", "exact"),
        ("k.js::K.a", "k.js::K.b", "exact"),
    }


def test_unique_attribute_name_resolves_by_name_and_ambiguous_ones_drop() -> None:
    files = {
        "a.py": "class A:\n    def ping(self):\n        pass\n\n    def twin(self):\n        pass\n",
        "b.py": "class B:\n    def twin(self):\n        pass\n",
        "c.py": "def use(x):\n    x.ping()\n    x.twin()\n    ping()\n    undefined()\n",
    }

    assert edges(files) == {("c.py::use", "a.py::A.ping", "name")}


def test_name_resolution_never_crosses_language_families() -> None:
    files = {
        "a.ts": "export class View {\n  render() {}\n}\n",
        "b.py": "def go(view):\n    view.render()\n",
    }

    assert edges(files) == set()


def test_import_dotted_module_then_call_through_it() -> None:
    files = {
        "src/a/__init__.py": "",
        "src/a/b.py": "def f():\n    pass\n",
        "app.py": "import a.b\nimport a.b as alias\n\n\ndef go():\n    a.b.f()\n    alias.f()\n",
    }

    assert edges(files) == {("app.py::go", "src/a/b.py::f", "exact")}
    assert len(Index({p: parse(p, t) for p, t in files.items()}).resolve_all()) == 2


def test_python_relative_imports() -> None:
    files = {
        "pkg/__init__.py": "from .core import Engine\n",
        "pkg/core.py": "class Engine:\n    def start(self):\n        pass\n",
        "pkg/sub/__init__.py": "",
        "pkg/sub/mod.py": (
            "from .. import core\n"
            "from ..core import Engine as E\n"
            "from . import sibling\n"
            "\n\ndef go():\n"
            "    core.Engine()\n"
            "    E.start(None)\n"
            "    sibling.helper()\n"
        ),
        "pkg/sub/sibling.py": "def helper():\n    pass\n",
        "app.py": "from pkg import Engine\n\n\ndef boot():\n    Engine()\n",
    }

    assert edges(files) == {
        ("pkg/sub/mod.py::go", "pkg/core.py::Engine", "exact"),
        ("pkg/sub/mod.py::go", "pkg/core.py::Engine.start", "exact"),
        ("pkg/sub/mod.py::go", "pkg/sub/sibling.py::helper", "exact"),
        ("app.py::boot", "pkg/core.py::Engine", "exact"),
    }


def test_external_imports_never_fall_back_to_name_resolution() -> None:
    files = {
        "paths.py": "def join(*parts):\n    pass\n",
        "app.py": "import os\nfrom json import loads\n\n\ndef go():\n    os.path.join('a')\n    loads('1')\n",
        "loads.py": "def loads(text):\n    pass\n",
    }

    assert edges(files) == set()


def test_star_import_resolves_bare_names() -> None:
    files = {
        "lib.py": "def f():\n    pass\n",
        "app.py": "from lib import *\n\n\ndef go():\n    f()\n",
    }

    assert edges(files) == {("app.py::go", "lib.py::f", "exact")}


def test_typescript_relative_imports_probe_extensions_and_index_files() -> None:
    files = {
        "web/src/lib.ts": "export function a() {}\n",
        "web/src/util/index.ts": "export function b() {}\n",
        "web/src/esm.ts": "export function c() {}\n",
        "web/src/widget.tsx": "export default function Widget() { return null; }\n",
        "web/src/legacy.mjs": "export function d() {}\n",
        "web/src/app.tsx": (
            'import { a } from "./lib";\n'
            'import * as util from "./util";\n'
            'import { c as see } from "./esm.js";\n'
            'import Widget from "./widget";\n'
            'import { d } from "./legacy.mjs";\n'
            'import { e } from "react";\n'
            "export function App() {\n"
            "  a(); util.b(); see(); Widget(); d(); e();\n"
            "}\n"
        ),
    }
    app = "web/src/app.tsx::App"

    assert edges(files) == {
        (app, "web/src/lib.ts::a", "exact"),
        (app, "web/src/util/index.ts::b", "exact"),
        (app, "web/src/esm.ts::c", "exact"),
        (app, "web/src/widget.tsx::Widget", "exact"),
        (app, "web/src/legacy.mjs::d", "exact"),
    }


def test_const_arrow_functions_are_symbols_only_at_top_level_or_in_a_class() -> None:
    source = (
        "export const top = () => helper();\n"
        "const expr = function () { return 1; };\n"
        "function helper() {\n"
        "  const local = () => top();\n"
        "  return local();\n"
        "}\n"
        "class C {\n"
        "  field = () => helper();\n"
        "}\n"
    )

    assert {(q, k) for q, k, _ in defs("m.ts", source)} == {
        ("top", "function"),
        ("expr", "function"),
        ("helper", "function"),
        ("C", "class"),
        ("C.field", "method"),
    }
    assert edges({"m.ts": source}) == {
        ("m.ts::top", "m.ts::helper", "exact"),
        ("m.ts::helper", "m.ts::top", "exact"),
        ("m.ts::C.field", "m.ts::helper", "exact"),
    }


def test_class_instantiation_is_a_call_to_the_class() -> None:
    files = {
        "m.py": "class Cart:\n    pass\n\n\ndef make():\n    return Cart()\n",
        "m.ts": "class Box {}\nfunction build() {\n  return new Box();\n}\n",
    }

    assert edges(files) == {
        ("m.py::make", "m.py::Cart", "exact"),
        ("m.ts::build", "m.ts::Box", "exact"),
    }


def test_calls_in_lambdas_and_comprehensions_belong_to_the_enclosing_def() -> None:
    source = (
        "def f(x):\n    pass\n\n\n"
        "def g(xs):\n"
        "    key = lambda x: f(x)\n"
        "    return [f(x) for x in xs]\n"
    )
    parsed = parse("m.py", source)

    assert {(c.scope, c.name, c.line) for c in parsed.calls} == {("g", "f", 6), ("g", "f", 7)}


def test_module_level_calls_have_no_scope() -> None:
    parsed = parse("m.py", "def f():\n    pass\n\n\nf()\n")

    assert [(c.scope, c.name, c.receiver) for c in parsed.calls] == [(None, "f", "bare")]


def test_syntax_errors_keep_the_definitions_tree_sitter_recovers() -> None:
    parsed = parse("m.py", "def good():\n    pass\n\n\ndef broken(:\n    ((\n")

    assert ("good", "function", (1, 2)) in {
        (d.qualname, d.kind, d.span) for d in parsed.definitions
    }
    assert parse_file("x.ts", b"export function ok() {}\nclass {{{ ]]]\n") is not None


def test_non_utf8_bytes_do_not_shift_lines() -> None:
    assert defs("m.py", b"# \xff\xfe caf\xe9\ndef f():\n    return '\xe9'\n") == {
        ("f", "function", (2, 3))
    }


def test_crlf_and_form_feed_line_endings_count_like_the_diff() -> None:
    assert defs("m.py", b"x = 1\r\n\r\ndef f():\r\n    pass\r\n") == {("f", "function", (3, 4))}
    assert defs("m.py", b"x = 1\n\x0c\ndef f():\n    pass\n") == {("f", "function", (4, 5))}


def test_duplicate_qualnames_merge_into_one_symbol_id() -> None:
    source = (
        "class A:\n"
        "    @property\n"
        "    def x(self):\n        return 1\n\n"
        "    @x.setter\n"
        "    def x(self, value):\n        pass\n"
    )
    parsed = parse("m.py", source)

    assert [d.qualname for d in parsed.definitions].count("A.x") == 2
    assert parsed.innermost(7) == "A.x" and parsed.innermost(1) == "A"
    assert parsed.innermost(5) == "A"


def test_commonjs_require_binds_modules_and_destructured_names() -> None:
    files = {
        "lib/x.js": "function f() {}\nmodule.exports = { f };\n",
        "lib/y.js": "function a() {}\nfunction b() {}\nmodule.exports = { a, b };\n",
        "lib/app.js": (
            'const x = require("./x");\n'
            'const { a, b: c } = require("./y");\n'
            "function go() {\n  x.f();\n  a();\n  c();\n}\n"
        ),
    }

    assert edges(files) == {
        ("lib/app.js::go", "lib/x.js::f", "exact"),
        ("lib/app.js::go", "lib/y.js::a", "exact"),
        ("lib/app.js::go", "lib/y.js::b", "exact"),
    }


def test_non_relative_require_binds_so_its_calls_drop() -> None:
    files = {
        "tests/helpers/fs.js": "function writeFile() {}\nmodule.exports = { writeFile };\n",
        "src/save.js": (
            'const fs = require("fs");\n'
            'const { join } = require("path");\n'
            "function save() {\n  fs.writeFile();\n  join();\n}\n"
        ),
        "src/join.js": "function join() {}\n",
    }

    assert edges(files) == set()


def test_only_require_calls_bind() -> None:
    files = {
        "lib/fs.ts": "export function writeFile() {}\n",
        "app.ts": 'const fs = load("./lib/fs");\nfunction go() {\n  fs.writeFile();\n}\n',
    }

    assert edges(files) == {("app.ts::go", "lib/fs.ts::writeFile", "name")}

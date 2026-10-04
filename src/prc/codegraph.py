"""Tree-sitter code graph: per-file definitions, calls and imports, resolved over one repo tree."""

from __future__ import annotations

import bisect
import itertools
import posixpath
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language as Grammar
from tree_sitter import Node, Parser, Query, QueryCursor

from prc.brief import Delta, kind_of
from prc.gitutil import run_git

if TYPE_CHECKING:
    from prc.changemap import Language, Resolution, SymbolKind

MAX_PARSE_BYTES = 512 * 1024
MAX_HOPS = 8
_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
Receiver = Literal["bare", "self", "other"]
Family = Literal["python", "js"]
Locate = Callable[["Index", str, str, tuple[str, ...]], "tuple[str, tuple[str, ...]] | None"]


@dataclass(frozen=True, slots=True)
class Definition:
    qualname: str
    kind: SymbolKind
    span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Call:
    scope: str | None
    name: str
    receiver: Receiver
    chain: tuple[str, ...]
    line: int


@dataclass(frozen=True, slots=True)
class Import:
    """`local` is bound to `name` of `module`; name None binds the module, "*" re-exports it."""

    local: str
    module: str
    name: str | None


@dataclass(frozen=True, slots=True)
class ParsedFile:
    language: Language
    definitions: tuple[Definition, ...]
    calls: tuple[Call, ...]
    imports: tuple[Import, ...]
    default_export: str | None

    def innermost(self, line: int) -> str | None:
        holding = [d for d in self.definitions if d.span[0] <= line <= d.span[1]]

        if not holding:
            return None

        return max(holding, key=lambda d: (d.span[0], -d.span[1])).qualname


@dataclass(frozen=True, slots=True)
class ResolvedCall:
    path: str
    scope: str | None
    target: str
    resolution: Resolution
    line: int


@dataclass(frozen=True, slots=True)
class Spec:
    language: Language
    family: Family
    grammar: Callable[[], object]
    definitions: str
    calls: str
    imports: str
    wrappers: frozenset[str]
    member: tuple[str, str, str]
    names: frozenset[str]
    selves: frozenset[str]
    locate: Locate


def _python_locate(
    index: Index, importer: str, module: str, attrs: tuple[str, ...]
) -> tuple[str, tuple[str, ...]] | None:
    level = len(module) - len(module.lstrip("."))
    names = tuple(part for part in module[level:].split(".") if part) + attrs

    if not level:
        for cut in range(len(names), 0, -1):
            stems = index.python_suffixes.get(".".join(names[:cut]), ())

            if stems:
                return (index.python_files[stems[0]], names[cut:]) if len(stems) == 1 else None

        return None

    base = PurePosixPath(importer).parent

    if level - 1 > len(base.parts):
        return None

    for _ in range(level - 1):
        base = base.parent

    for cut in range(len(names), -1, -1):
        stem = str(PurePosixPath(base, *names[:cut]))

        if stem in index.python_files:
            return index.python_files[stem], names[cut:]

    return None


def _js_locate(
    index: Index, importer: str, module: str, attrs: tuple[str, ...]
) -> tuple[str, tuple[str, ...]] | None:
    if module not in (".", "..") and not module.startswith(("./", "../")):
        return None

    base = posixpath.normpath(posixpath.join(posixpath.dirname(importer), module))

    if base.startswith("../") or base == "..":
        return None

    stem, extension = posixpath.splitext(base)
    candidates = [base, *(base + ext for ext in JS_EXTENSIONS)]
    candidates += [f"{base}/index{ext}" for ext in JS_EXTENSIONS]

    if extension in JS_EXTENSIONS:
        candidates += [stem + ext for ext in JS_EXTENSIONS]

    found = next((path for path in candidates if path in index.files), None)

    return None if found is None else (found, attrs)


_PY_DEFINITIONS = """
(class_definition name: (identifier) @name) @class
(function_definition name: (identifier) @name) @function
"""
_PY_CALLS = """
(call function: (identifier) @name) @call
(call function: (attribute object: (_) @receiver attribute: (identifier) @name)) @call
"""
_PY_IMPORTS = """
(import_statement name: (dotted_name) @module) @plain
(import_statement name: (aliased_import name: (dotted_name) @module alias: (identifier) @local))
(import_from_statement module_name: (_) @module name: (dotted_name) @name)
(import_from_statement
  module_name: (_) @module
  name: (aliased_import name: (dotted_name) @name alias: (identifier) @local))
(import_from_statement module_name: (_) @module (wildcard_import) @star)
"""
_BOUND_FUNCTION = "value: [(arrow_function) (function_expression)]"
_JS_DEFINITIONS = f"""
(function_declaration name: (identifier) @name) @function
(generator_function_declaration name: (identifier) @name) @function
(class_declaration name: (_) @name) @class
(class_body (method_definition name: (_) @name) @function)
(program (lexical_declaration (variable_declarator name: (identifier) @name {_BOUND_FUNCTION}) @function))
(program (variable_declaration (variable_declarator name: (identifier) @name {_BOUND_FUNCTION}) @function))
(program (export_statement declaration: (lexical_declaration
  (variable_declarator name: (identifier) @name {_BOUND_FUNCTION}) @function)))
(program (export_statement declaration: (variable_declaration
  (variable_declarator name: (identifier) @name {_BOUND_FUNCTION}) @function)))
"""
_JS_ONLY_DEFINITIONS = f"""
(class_body (field_definition property: (property_identifier) @name {_BOUND_FUNCTION}) @function)
"""
_TS_ONLY_DEFINITIONS = f"""
(class_body (public_field_definition name: (property_identifier) @name {_BOUND_FUNCTION}) @function)
(abstract_class_declaration name: (type_identifier) @name) @class
"""
_JS_CALLS = """
(call_expression function: (identifier) @name) @call
(call_expression function: (member_expression
  object: (_) @receiver
  property: [(property_identifier) (private_property_identifier)] @name)) @call
(new_expression constructor: (identifier) @name) @call
(new_expression constructor: (member_expression
  object: (_) @receiver property: (property_identifier) @name)) @call
"""
_REQUIRE = """(call_expression
  function: (identifier) @require (#eq? @require "require")
  arguments: (arguments . (string (string_fragment) @module) .))"""
_JS_IMPORTS = f"""
(import_statement (import_clause (identifier) @local) source: (string (string_fragment) @module)) @default
(import_statement
  (import_clause (named_imports (import_specifier name: (_) @name alias: (_)? @local)))
  source: (string (string_fragment) @module))
(import_statement
  (import_clause (namespace_import (identifier) @local))
  source: (string (string_fragment) @module))
(export_statement
  (export_clause (export_specifier name: (_) @name alias: (_)? @local))
  source: (string (string_fragment) @module))
(export_statement "*" source: (string (string_fragment) @module)) @star
(export_statement "default" declaration: [
  (function_declaration name: (identifier) @exported)
  (generator_function_declaration name: (identifier) @exported)
  (class_declaration name: (_) @exported)])
(export_statement "default" value: (identifier) @exported)
(variable_declarator name: (identifier) @local value: {_REQUIRE})
(variable_declarator
  name: (object_pattern [
    (shorthand_property_identifier_pattern) @name
    (pair_pattern key: (property_identifier) @name value: (identifier) @local)])
  value: {_REQUIRE})
"""

_PYTHON = Spec(
    language="python",
    family="python",
    grammar=tree_sitter_python.language,
    definitions=_PY_DEFINITIONS,
    calls=_PY_CALLS,
    imports=_PY_IMPORTS,
    wrappers=frozenset({"decorated_definition"}),
    member=("attribute", "object", "attribute"),
    names=frozenset({"identifier"}),
    selves=frozenset({"self", "cls"}),
    locate=_python_locate,
)


def _js(language: Language, grammar: Callable[[], object], definitions: str) -> Spec:
    return Spec(
        language=language,
        family="js",
        grammar=grammar,
        definitions=_JS_DEFINITIONS + definitions,
        calls=_JS_CALLS,
        imports=_JS_IMPORTS,
        wrappers=frozenset({"export_statement", "lexical_declaration", "variable_declaration"}),
        member=("member_expression", "object", "property"),
        names=frozenset({"identifier", "this"}),
        selves=frozenset({"this"}),
        locate=_js_locate,
    )


_JAVASCRIPT = _js("javascript", tree_sitter_javascript.language, _JS_ONLY_DEFINITIONS)
_TYPESCRIPT = _js("typescript", tree_sitter_typescript.language_typescript, _TS_ONLY_DEFINITIONS)
_TSX = _js("tsx", tree_sitter_typescript.language_tsx, _TS_ONLY_DEFINITIONS)

LANGUAGES: dict[str, Spec] = {
    ".py": _PYTHON,
    ".pyi": _PYTHON,
    ".ts": _TYPESCRIPT,
    ".tsx": _TSX,
    ".mts": _TYPESCRIPT,
    ".cts": _TYPESCRIPT,
    ".js": _JAVASCRIPT,
    ".jsx": _JAVASCRIPT,
    ".mjs": _JAVASCRIPT,
    ".cjs": _JAVASCRIPT,
}
JS_EXTENSIONS = tuple(ext for ext, spec in LANGUAGES.items() if spec.family == "js")


def spec_of(path: str) -> Spec | None:
    return LANGUAGES.get(posixpath.splitext(path)[1])


def language_of(path: str) -> Language | None:
    spec = spec_of(path)

    return None if spec is None else spec.language


@dataclass(frozen=True, slots=True)
class _Compiled:
    parser: Parser
    definitions: Query
    calls: Query
    imports: Query


@cache
def _compiled(language: Language) -> _Compiled:
    spec = next(spec for spec in LANGUAGES.values() if spec.language == language)
    grammar = Grammar(spec.grammar())

    return _Compiled(
        Parser(grammar),
        Query(grammar, spec.definitions),
        Query(grammar, spec.calls),
        Query(grammar, spec.imports),
    )


def _key(node: Node) -> tuple[int, int, str]:
    return node.start_byte, node.end_byte, node.type


def parse_file(path: str, data: bytes) -> ParsedFile | None:
    """None for an unsupported extension, a file over the size limit, or binary content."""

    spec = spec_of(path)

    if spec is None or len(data) > MAX_PARSE_BYTES or b"\x00" in data[:8192]:
        return None

    # The diff records decode with "replace" and number lines with str.splitlines; parse the
    # same text so byte offsets map onto the diff's line numbers.
    text = data.decode("utf-8", "replace")
    source = text.encode()
    starts = list(
        itertools.accumulate((len(line.encode()) for line in text.splitlines(True)), initial=0)
    )
    compiled = _compiled(spec.language)
    root = compiled.parser.parse(source).root_node

    def line_of(offset: int) -> int:
        return bisect.bisect_right(starts, offset)

    def text_of(node: Node) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", "replace")

    found: dict[tuple[int, int, str], tuple[Node, Node, str, bool]] = {}

    for _, captures in QueryCursor(compiled.definitions).matches(root):
        is_class = "class" in captures
        node = captures["class" if is_class else "function"][0]
        outer = node

        while outer.parent is not None and outer.parent.type in spec.wrappers:
            outer = outer.parent

        found.setdefault(_key(node), (node, outer, text_of(captures["name"][0]), is_class))

    owners: dict[tuple[int, int, str], Definition] = {}
    definitions: list[Definition] = []

    def enclosing(node: Node) -> Definition | None:
        parent = node.parent

        while parent is not None:
            owner = owners.get(_key(parent))

            if owner is not None:
                return owner

            parent = parent.parent

        return None

    for node, outer, name, is_class in sorted(
        found.values(), key=lambda entry: (entry[1].start_byte, -entry[1].end_byte)
    ):
        parent = enclosing(outer)
        kind: SymbolKind = (
            "class" if is_class else "method" if parent and parent.kind == "class" else "function"
        )
        span = (line_of(outer.start_byte), line_of(max(outer.end_byte - 1, outer.start_byte)))
        definition = Definition(name if parent is None else f"{parent.qualname}.{name}", kind, span)
        owners[_key(node)] = owners[_key(outer)] = definition
        definitions.append(definition)

    calls: list[Call] = []

    for _, captures in QueryCursor(compiled.calls).matches(root):
        name_node = captures["name"][0]
        owner = enclosing(captures["call"][0])
        receivers = captures.get("receiver")
        chain = () if not receivers else _chain(receivers[0], spec, text_of)
        receiver: Receiver = (
            "bare"
            if not receivers
            else "self"
            if len(chain) == 1 and chain[0] in spec.selves
            else "other"
        )
        calls.append(
            Call(
                None if owner is None else owner.qualname,
                text_of(name_node),
                receiver,
                chain,
                line_of(name_node.start_byte),
            )
        )

    imports: list[Import] = []
    default_export: str | None = None

    for _, captures in QueryCursor(compiled.imports).matches(root):
        if "exported" in captures:
            default_export = text_of(captures["exported"][0])
            continue

        module = "".join(text_of(captures["module"][0]).split())
        imported: str | None = None

        if "star" in captures:
            imported = "*"
        elif "default" in captures:
            imported = "default"
        elif "name" in captures:
            imported = text_of(captures["name"][0])

        if "local" in captures:
            local = text_of(captures["local"][0])
        elif "plain" in captures:
            local = module = module.split(".")[0]
        else:
            local = imported or module

        imports.append(Import(local, module, imported))

    return ParsedFile(
        spec.language,
        tuple(definitions),
        tuple(sorted(calls, key=lambda c: (c.line, c.name, c.chain, c.scope or ""))),
        tuple(imports),
        default_export,
    )


def _chain(node: Node, spec: Spec, text_of: Callable[[Node], str]) -> tuple[str, ...]:
    """A receiver as dotted identifiers, or () when it is not a plain name chain."""

    member, object_field, property_field = spec.member
    parts: list[str] = []

    while node.type == member:
        prop = node.child_by_field_name(property_field)
        obj = node.child_by_field_name(object_field)

        if prop is None or obj is None:
            return ()

        parts.append(text_of(prop))
        node = obj

    if node.type not in spec.names:
        return ()

    parts.append(text_of(node))

    return tuple(reversed(parts))


class Index:
    """One tree's parsed files, answering call resolution in the PLANS rule 4 order."""

    def __init__(self, files: Mapping[str, ParsedFile]) -> None:
        self.files = dict(sorted(files.items()))
        self.definitions: dict[str, dict[str, Definition]] = {}
        self.exported: dict[str, frozenset[str]] = {}
        self.bindings: dict[str, dict[str, Import]] = {}
        self.stars: dict[str, tuple[Import, ...]] = {}
        self.python_files: dict[str, str] = {}
        suffixes: dict[str, list[str]] = {}
        names: dict[tuple[Family, str], set[str]] = {}

        for path, parsed in self.files.items():
            merged: dict[str, Definition] = {}

            for d in parsed.definitions:
                seen = merged.get(d.qualname)
                merged[d.qualname] = (
                    d
                    if seen is None
                    else Definition(
                        d.qualname,
                        seen.kind,
                        (min(seen.span[0], d.span[0]), max(seen.span[1], d.span[1])),
                    )
                )

            self.definitions[path] = merged
            self.exported[path] = frozenset(
                qualname
                for qualname in merged
                if all(
                    merged.get(prefix) is not None and merged[prefix].kind == "class"
                    for prefix in _prefixes(qualname)
                )
            )
            self.bindings[path] = {i.local: i for i in parsed.imports if i.name != "*"}
            self.stars[path] = tuple(i for i in parsed.imports if i.name == "*")
            family = LANGUAGES[posixpath.splitext(path)[1]].family

            for qualname in self.exported[path]:
                names.setdefault((family, qualname.rsplit(".", 1)[-1]), set()).add(
                    f"{path}::{qualname}"
                )

        for path in sorted(self.files, key=lambda p: (p.endswith(".pyi"), p)):
            stem, extension = posixpath.splitext(path)

            if extension not in (".py", ".pyi"):
                continue

            if posixpath.basename(stem) == "__init__":
                stem = posixpath.dirname(stem)

            if stem and stem not in self.python_files:
                self.python_files[stem] = path
                parts = stem.split("/")

                for start in range(len(parts)):
                    suffixes.setdefault(".".join(parts[start:]), []).append(stem)

        self.python_suffixes = {dotted: tuple(stems) for dotted, stems in suffixes.items()}
        self.by_name = {key: tuple(sorted(ids)) for key, ids in names.items()}

    def resolve_all(self) -> tuple[ResolvedCall, ...]:
        resolved: list[ResolvedCall] = []

        for path, parsed in self.files.items():
            for call in parsed.calls:
                hit = self.resolve(path, call)

                if hit is not None:
                    resolved.append(ResolvedCall(path, call.scope, hit[0], hit[1], call.line))

        return tuple(resolved)

    def resolve(self, path: str, call: Call) -> tuple[str, Resolution] | None:
        local = self.definitions[path]

        if call.receiver == "bare":
            scoped = self._scoped(path, call.scope, call.name)

            if scoped is not None:
                return f"{path}::{scoped}", "exact"

            return self._imported(path, call.name, ())

        if call.receiver == "self":
            owner = self._enclosing_class(path, call.scope)

            if owner is None:
                return None

            if f"{owner}.{call.name}" in local:
                return f"{path}::{owner}.{call.name}", "exact"

        elif not call.chain:
            return None

        else:
            root, rest = call.chain[0], (*call.chain[1:], call.name)
            scoped = self._scoped(path, call.scope, root)

            if scoped is not None:
                qualname = ".".join((scoped, *rest))

                if qualname in local:
                    return f"{path}::{qualname}", "exact"

            elif root in self.bindings[path]:
                return self._imported(path, root, rest)

        named = self._named(path, call)

        return None if named is None else (named, "name")

    def _named(self, path: str, call: Call) -> str | None:
        """The one candidate rule 4.4 leaves for an unresolved `obj.x()` or inherited `self.x()`."""

        if call.name.startswith("__") and call.name.endswith("__"):
            return None

        receiver = _words(call.chain[-1]) if call.receiver == "other" else frozenset()

        def fits(candidate: str) -> bool:
            where, _, qualname = candidate.rpartition("::")
            owner = qualname.rpartition(".")[0]

            if call.receiver == "self":
                return self.definitions[where][qualname].kind == "method"

            return bool(receiver) and receiver <= _words(
                owner.rpartition(".")[2] if owner else _module_name(where)
            )

        family = LANGUAGES[posixpath.splitext(path)[1]].family
        found = [c for c in self.by_name.get((family, call.name), ()) if fits(c)]

        return found[0] if len(found) == 1 else None

    def _imported(
        self, path: str, local: str, rest: tuple[str, ...]
    ) -> tuple[str, Resolution] | None:
        binding = self.bindings[path].get(local)
        targets: Iterable[str | None] = (
            [self._follow(path, binding, rest, 0)]
            if binding is not None
            else (self._follow(path, star, (local, *rest), 0) for star in self.stars[path])
        )
        target = next((t for t in targets if t is not None), None)

        return None if target is None else (target, "exact")

    def _follow(self, path: str, binding: Import, rest: tuple[str, ...], hops: int) -> str | None:
        attrs = rest if binding.name in (None, "*") else (binding.name, *rest)
        located = LANGUAGES[posixpath.splitext(path)[1]].locate(self, path, binding.module, attrs)

        return None if located is None else self._lookup(*located, hops)

    def _lookup(self, path: str, attrs: tuple[str, ...], hops: int) -> str | None:
        parsed = self.files.get(path)

        if parsed is None or not attrs:
            return None

        if attrs[0] == "default" and parsed.default_export is not None:
            attrs = (parsed.default_export, *attrs[1:])

        qualname = ".".join(attrs)

        if qualname in self.exported[path]:
            return f"{path}::{qualname}"

        if hops >= MAX_HOPS:
            return None

        binding = self.bindings[path].get(attrs[0])

        if binding is not None:
            return self._follow(path, binding, attrs[1:], hops + 1)

        return next(
            (
                target
                for star in self.stars[path]
                if (target := self._follow(path, star, attrs, hops + 1)) is not None
            ),
            None,
        )

    def _scoped(self, path: str, scope: str | None, name: str) -> str | None:
        """The definition a bare name means in `scope`: own scope, then enclosing non-class ones."""

        local = self.definitions[path]
        scopes = [] if scope is None else [scope]
        scopes += [p for p in _prefixes(scope or "") if p in local and local[p].kind != "class"]
        scopes.append("")

        return next(
            (q for s in scopes if (q := f"{s}.{name}" if s else name) in local),
            None,
        )

    def _enclosing_class(self, path: str, scope: str | None) -> str | None:
        local = self.definitions[path]
        scopes = [] if scope is None else [scope, *_prefixes(scope)]

        return next((s for s in scopes if s in local and local[s].kind == "class"), None)


@cache
def _words(name: str) -> frozenset[str]:
    """Lowercased snake_case, camelCase, PascalCase and digit-run parts of an identifier."""

    return frozenset(part.lower() for part in _WORD.findall(name))


def _module_name(path: str) -> str:
    stem = posixpath.splitext(posixpath.basename(path))[0]

    return posixpath.basename(posixpath.dirname(path)) if stem in ("__init__", "index") else stem


def _prefixes(qualname: str) -> list[str]:
    """Proper dotted prefixes, innermost first: `a.b.c` gives `a.b`, `a`."""

    parts = qualname.split(".")

    return [".".join(parts[:end]) for end in range(len(parts) - 1, 0, -1)]


@dataclass(frozen=True, slots=True)
class TreeBlob:
    path: str
    oid: str
    size: int


def tree_blobs(repo: Path, commit: str) -> tuple[TreeBlob, ...]:
    raw = run_git(repo, "ls-tree", "-r", "-z", "-l", "--end-of-options", commit)
    blobs: list[TreeBlob] = []

    for entry in raw.split(b"\x00"):
        if not entry:
            continue

        meta, _, name = entry.partition(b"\t")
        mode, kind, oid, size = meta.split()

        if kind == b"blob" and mode in (b"100644", b"100755"):
            blobs.append(TreeBlob(name.decode("utf-8", "surrogateescape"), oid.decode(), int(size)))

    return tuple(blobs)


def read_blobs(repo: Path, oids: Iterable[str]) -> dict[str, bytes]:
    """Blob contents in one `git cat-file --batch` call."""

    wanted = sorted(set(oids))

    if not wanted:
        return {}

    raw = run_git(
        repo, "cat-file", "--batch", input_bytes="".join(f"{o}\n" for o in wanted).encode()
    )
    blobs: dict[str, bytes] = {}
    cursor = 0

    while cursor < len(raw):
        end = raw.index(b"\n", cursor)
        header = raw[cursor:end].split()
        cursor = end + 1

        if len(header) == 3:
            size = int(header[2])
            blobs[header[0].decode()] = raw[cursor : cursor + size]
            cursor += size + 1

    return blobs


ParseCache = dict[tuple[str, str], ParsedFile | None]


def index_tree(repo: Path, commit: str, skip: frozenset[str], parsed: ParseCache) -> Index:
    """Index every parseable source file in `commit`; `parsed` is shared across trees by blob id."""

    blobs = [
        blob
        for blob in tree_blobs(repo, commit)
        if blob.path not in skip
        and blob.size <= MAX_PARSE_BYTES
        and spec_of(blob.path) is not None
        and kind_of(Delta(blob.path, False, 0, 0)) != "generated"
    ]
    keys = {blob.path: (blob.oid, str(language_of(blob.path))) for blob in blobs}
    contents = read_blobs(repo, (oid for oid, lang in keys.values() if (oid, lang) not in parsed))

    for blob in blobs:
        key = keys[blob.path]

        if key not in parsed:
            parsed[key] = parse_file(blob.path, contents.get(blob.oid, b""))

    return Index(
        {path: result for path, key in keys.items() if (result := parsed[key]) is not None}
    )

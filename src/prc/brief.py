from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from prc.snapshot import Acquisition

Kind = Literal["code", "test", "docs", "config", "generated", "opaque"]
MismatchKind = Literal[
    "changed_claim_not_in_diff",
    "symbol_claim_not_found",
    "test_claim_vs_ci",
    "tests_claim_no_test_files",
]
CheckState = Literal["passed", "failed", "pending"]

MAX_POINTERS = 3
MANIFEST_LINES = 3


@dataclass(frozen=True, slots=True)
class Delta:
    path: str
    opaque: bool
    added: int
    removed: int
    diff: str = ""
    head: str = ""


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    state: CheckState


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    kind: Kind
    added: int
    removed: int
    named: bool
    sensitive: str | None


@dataclass(frozen=True, slots=True)
class Mismatch:
    kind: MismatchKind
    quote: str
    fact: str
    subjects: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Pointer:
    path: str
    reason: str
    lines: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Brief:
    pr: str
    title: str
    head_sha: str
    files: tuple[FileChange, ...]
    checks: tuple[Check, ...]
    mismatches: tuple[Mismatch, ...]
    look_first: tuple[Pointer, ...]


@dataclass(frozen=True, slots=True)
class Unit:
    text: str
    checked: bool | None


Rule = tuple[Callable[[Delta], bool], Kind]


def _path(pattern: str) -> Callable[[Delta], bool]:
    rx = re.compile(pattern, re.IGNORECASE)

    return lambda delta: rx.search(delta.path) is not None


_LOCKFILE = r"(^|/)(package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|uv\.lock|poetry\.lock|pdm\.lock|Pipfile\.lock|Cargo\.lock|Gemfile\.lock|composer\.lock|go\.sum|flake\.lock)$|\.lock$"
_MANIFEST = r"(^|/)(package\.json|pyproject\.toml|requirements[^/]*\.txt|Pipfile|Gemfile|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|composer\.json|setup\.py|setup\.cfg)$"
_DOCKER = r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*\.ya?ml|\.dockerignore)$"
_CI = r"(^|/)(\.gitlab-ci\.yml|\.circleci/|Jenkinsfile|azure-pipelines\.yml|\.travis\.yml|tox\.ini)"

KIND_RULES: tuple[Rule, ...] = (
    (lambda delta: delta.opaque, "opaque"),
    (
        _path(
            _LOCKFILE
            + r"|\.snap$|(^|/)__snapshots__/|\.min\.(js|css)$|(^|/)(dist|vendor)/"
            + r"|_pb2(_grpc)?\.pyi?$|\.pb\.go$|\.generated\.|(^|/)generated/|\.g\.dart$"
        ),
        "generated",
    ),
    (
        _path(
            r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]*$|_tests?\.[a-z]+$"
            r"|\.(test|spec)\.[a-z]+$|(^|/)conftest\.py$|Tests?\.(java|kt|cs)$"
        ),
        "test",
    ),
    (
        _path(
            r"^\.github/|"
            + _MANIFEST
            + "|"
            + _DOCKER
            + "|"
            + _CI
            + r"|\.(toml|ini|cfg|ya?ml|json|tf)$|(^|/)\.env|(^|/)Makefile$"
        ),
        "config",
    ),
    (
        _path(r"\.(md|markdown|rst|txt|adoc)$|(^|/)docs?/|(^|/)(LICENSE|COPYING|NOTICE)[^/]*$"),
        "docs",
    ),
    (lambda delta: True, "code"),
)


@dataclass(frozen=True, slots=True)
class SensitiveRule:
    rx: re.Pattern[str]
    reason: str
    shows_added: bool


SENSITIVE_RULES: tuple[SensitiveRule, ...] = tuple(
    SensitiveRule(re.compile(pattern, re.IGNORECASE), reason, lines)
    for pattern, reason, lines in (
        (
            r"(^|/)(\.gitleaksignore|\.gitleaks\.toml|\.secrets\.baseline|\.gitguardian\.ya?ml"
            r"|\.trufflehogignore)$",
            "secret-scanner allowlist",
            False,
        ),
        (
            r"(^|/)(\.npmrc|\.pypirc|\.yarnrc(\.ya?ml)?)$",
            "package registry config",
            False,
        ),
        (r"^\.github/workflows/", "CI workflow", False),
        (r"^\.github/", "repository automation config", False),
        (_MANIFEST, "dependency manifest", True),
        (
            _DOCKER + r"|\.tfvars?$|\.tf$|(^|/)(k8s|kubernetes|helm|terraform|infra)/",
            "Docker or infrastructure",
            False,
        ),
        (r"(^|/)(migrations?|alembic)/|\.sql$", "migration or SQL", False),
        (r"(^|/)\.env|\.(pem|key|p12|pfx)$", "env or secret file", False),
        (
            r"(^|[/_.-])(auth|authn|authz|authentication|authorization|oauth|login|passwords?"
            r"|credentials?|secrets?|tokens?|security|crypto|permissions?|acl|jwt|sso)([/_.-]|$)",
            "auth or security path",
            False,
        ),
        (_CI, "CI config", False),
    )
)


def kind_of(delta: Delta) -> Kind:
    return next(kind for matches, kind in KIND_RULES if matches(delta))


def sensitive_rule(path: str) -> SensitiveRule | None:
    return next((rule for rule in SENSITIVE_RULES if rule.rx.search(path)), None)


def reason_of(path: str) -> str | None:
    rule = sensitive_rule(path)

    return None if rule is None else rule.reason


_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
_DETAILS = re.compile(r"<details\b[^>]*>|</details\s*>", re.IGNORECASE)
_QUOTE = re.compile(r"^\s{0,3}>")
_HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[([ xX])\]\s+)?(\S.*?)\s*$")
_TABLE = re.compile(r"^\s*\|")
_TABLE_RULE = re.compile(r"^\s*\|[\s|:-]*$")
_EMPHASIS = re.compile(r"\*\*|__")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")


def _unemphasize(line: str) -> str:
    parts = re.split(r"(`[^`\n]*`)", line)

    return "".join(p if i % 2 else _EMPHASIS.sub("", p) for i, p in enumerate(parts))


def _drop_fences(text: str) -> str:
    out: list[str] = []
    fence = ""

    for line in text.splitlines():
        opener = _FENCE.match(line)

        if not fence:
            if opener:
                fence = opener.group(1)
            else:
                out.append(line)
        elif opener and set(line.strip()) == {fence[0]} and len(line.strip()) >= len(fence):
            fence = ""

    return "\n".join(out)


def _drop_details(text: str) -> str:
    out: list[str] = []
    depth = 0
    pos = 0

    for tag in _DETAILS.finditer(text):
        opening = tag.group(0)[1] != "/"

        if opening and depth == 0:
            out.append(text[pos : tag.start()])
            depth = 1
        elif opening:
            depth += 1
        elif depth > 0:
            depth -= 1

            if depth == 0:
                pos = tag.end()

    if depth == 0:
        out.append(text[pos:])

    return "".join(out)


def units_of(title: str, body: str) -> tuple[Unit, ...]:
    visible = _drop_details(_COMMENT.sub("", _drop_fences(body)))
    units = [Unit(title.strip(), None)] if title.strip() else []
    paragraph: list[str] = []

    def flush() -> None:
        text = " ".join(paragraph)
        paragraph.clear()
        units.extend(Unit(part.strip(), None) for part in _SENTENCE_END.split(text) if part.strip())

    for raw in visible.splitlines():
        line = _unemphasize(raw)
        bullet = _BULLET.match(line)

        if not line.strip() or _HEADING.match(line) or _QUOTE.match(line):
            flush()
        elif _TABLE.match(line):
            flush()

            if not _TABLE_RULE.match(line):
                units.append(Unit(line.strip(), None))
        elif bullet:
            flush()
            box = bullet.group(1)
            units.append(Unit(bullet.group(2), None if box is None else box in "xX"))
        else:
            paragraph.append(line.strip())

    flush()

    return tuple(units)


_URL = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)\S+", re.IGNORECASE)
_TICKS = re.compile(r"`([^`\n]+)`")
_EXTS = (
    "py|pyi|js|jsx|ts|tsx|mjs|cjs|md|rst|txt|toml|ini|cfg|ya?ml|json|lock|sh|go|rs|java|kt|c|h"
    "|cc|cpp|hpp|cs|rb|php|sql|html|css|scss|tf|swift|scala|lua|ex|exs|vue|svelte|xml|gradle"
    "|proto|env"
)
_FILE_EXT = re.compile(rf"\.(?:{_EXTS})$", re.IGNORECASE)
_BARE = re.compile(
    rf"(?<![\w@/.:-])((?:[\w.-]+/)*[\w.-]+\.(?:{_EXTS})|(?:[\w.-]+/)+)(?![\w@-])", re.IGNORECASE
)
_LINE_SUFFIX = re.compile(r"(?:::?[\w$]+|#[\w$.-]+)+$")
_PATH_CHARS = re.compile(r"[\w.+@\[\]()/-]+")
_DOMAIN = re.compile(r"\.(?:com|org|io|dev|ai|app|net|co)$", re.IGNORECASE)
_IDENT = re.compile(r"^([A-Za-z_$][\w$]*(?:(?:\.|::|->|#)[A-Za-z_$][\w$]*)*)\s*(?:\(.*\))?$")
_SEGMENTS = re.compile(r"\.|::|->|#")


def _is_path(token: str) -> bool:
    segments = [part for part in token.split("/") if part]

    if (
        not segments
        or not re.search(r"[^\W\d_]", token)
        or not _PATH_CHARS.fullmatch(token)
        or token.startswith("@")
        or _DOMAIN.search(segments[0])
    ):
        return False

    return len(segments) > 1 or not token.startswith("/")


def path_tokens(text: str) -> tuple[str, ...]:
    clean = _URL.sub(" ", text)
    found: list[str] = []

    for tick in _TICKS.findall(clean):
        token = _LINE_SUFFIX.sub("", tick.strip())

        if token and ("/" in token or _FILE_EXT.search(token)):
            found.append(token)

    found.extend(match.group(1) for match in _BARE.finditer(_TICKS.sub(" ", clean)))

    return tuple(dict.fromkeys(token for token in found if _is_path(token)))


def symbol_objects(text: str) -> tuple[str, ...]:
    names: list[str] = []

    for match in _SYMBOL_OBJECT.finditer(_URL.sub(" ", text)):
        token = match.group(1).strip()
        shape = _IDENT.match(token)

        if shape and not _FILE_EXT.search(token.split("(", 1)[0]):
            name = _SEGMENTS.split(shape.group(1))[-1]

            if len(name) > 1:
                names.append(name)

    return tuple(dict.fromkeys(names))


def hits(token: str, path: str) -> bool:
    target = "/" + token.removeprefix("./").lstrip("/").rstrip("/")
    full = "/" + path

    return (not token.endswith("/") and full.endswith(target)) or target + "/" in full


class Tree:
    def __init__(self, paths: Iterable[str]) -> None:
        self.files: set[str] = set()
        self.dirs: set[str] = set()

        for path in paths:
            parts = path.split("/")

            for i in range(len(parts)):
                self.files.add("/".join(parts[i:]))

                for j in range(i + 1, len(parts)):
                    self.dirs.add("/".join(parts[i:j]))

    def has(self, token: str) -> bool:
        key = token.removeprefix("./").strip("/")

        return key in self.dirs or (not token.endswith("/") and key in self.files)


_CHANGE_VERB = re.compile(
    r"(?<![\w-])(?:add(?:s|ed|ing)?|updat(?:e|es|ed|ing)|modif(?:y|ies|ied|ying)|chang(?:e|es|ed|ing)"
    r"|fix(?:es|ed|ing)?|bump(?:s|ed|ing)?|remov(?:e|es|ed|ing)|delet(?:e|es|ed|ing)"
    r"|renam(?:e|es|ed|ing)|mov(?:e|es|ed|ing)|replac(?:e|es|ed|ing)|creat(?:e|es|ed|ing)"
    r"|edit(?:s|ed|ing)?|rewr(?:ite|ites|ote|itten|iting)|refactor(?:s|ed|ing)?)(?![\w-])"
    r"|→|->",
    re.IGNORECASE,
)
_SYMBOL_OBJECT = re.compile(
    r"(?<![\w-])(?:add(?:s|ed|ing)?|creat(?:e|es|ed|ing)|introduc(?:e|es|ed|ing)|new"
    r"|remov(?:e|es|ed|ing)|delet(?:e|es|ed|ing)|renam(?:e|es|ed|ing))(?![\w-])"
    r"(?:\s+(?:a|an|the|new|old|this|that|existing|public|private|static|async|helper"
    r"|function|method|class|type|constant)(?![\w-])){0,3}\s+`([^`\n]+)`",
    re.IGNORECASE,
)
_HEDGE = re.compile(
    r"(?<![\w-])(?:not|no|never|without|kept|unchanged|untouched|already|would|could|instead)"
    r"(?![\w-])|n't",
    re.IGNORECASE,
)
_CI_NOUN = re.compile(
    r"\b(?:tests?|test suite|lint(?:ing|er)?|type-?check(?:s|ing)?|type checks?|builds?|ci"
    r"|checks?|pipeline)\b",
    re.IGNORECASE,
)
_PASSED = re.compile(
    r"\b(?:pass(?:es|ed|ing)?|green|succe(?:ed|eds|eded|ssful(?:ly)?)|clean)\b", re.IGNORECASE
)
_TEST_NOUN = re.compile(r"\b(?:tests?|test (?:cases?|suite|coverage)|specs?)\b", re.IGNORECASE)
_TEST_VERB = re.compile(
    r"\b(?:add(?:s|ed|ing)?|writ(?:e|es|ing)|wrote|written|updat(?:e|es|ed|ing)"
    r"|creat(?:e|es|ed|ing)|includ(?:e|es|ed|ing)|extend(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
_NEGATED = re.compile(
    r"\b(?:not|no|never|without|fail\w*|todo|need|needs|should|will|plan|planned)\b|n't",
    re.IGNORECASE,
)
_FAILED = frozenset({"failure", "timed_out", "cancelled", "action_required", "startup_failure"})
_PASSING = frozenset({"success", "neutral", "skipped"})
_DEFINED = re.compile(
    r"^\+\s*(?:(?:export|public|private|static|async|pub)\s+)*"
    r"(?:def|class|function|fn|func|struct|enum|trait|interface|type|const|let|var)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)


def _mismatches(
    units: tuple[Unit, ...], deltas: tuple[Delta, ...], files: tuple[FileChange, ...],
    checks: tuple[Check, ...], tree: Tree,
) -> tuple[Mismatch, ...]:  # fmt: skip
    found: dict[tuple[str, str], Mismatch] = {}
    failed = tuple(check.name for check in checks if check.state == "failed")
    has_tests = any(file.kind == "test" for file in files)
    opaque = any(delta.opaque for delta in deltas)

    def add(unit: Unit, kind: MismatchKind, fact: str, subjects: tuple[str, ...] = ()) -> None:
        found.setdefault((kind, unit.text), Mismatch(kind, unit.text, fact, subjects))

    for unit in units:
        if unit.checked is False:
            continue

        text = _URL.sub(" ", unit.text)
        bare = _TICKS.sub(" ", text)
        hedged = _HEDGE.search(bare) is not None

        if not hedged and _CHANGE_VERB.search(bare):
            missing = tuple(
                token
                for token in path_tokens(text)
                if tree.has(token) and not any(hits(token, delta.path) for delta in deltas)
            )

            if missing:
                add(unit, "changed_claim_not_in_diff", "no changed file matches", missing)

        if not hedged and not opaque:
            absent = tuple(
                name
                for name in symbol_objects(text)
                if not any(name in delta.diff or name in delta.head for delta in deltas)
            )

            if absent:
                add(unit, "symbol_claim_not_found", "no changed line or file contains", absent)

        negated = _NEGATED.search(text)

        if _CI_NOUN.search(text) and _PASSED.search(text) and not negated:
            if failed:
                add(unit, "test_claim_vs_ci", "these checks failed on this commit:", failed)
            elif not checks:
                add(unit, "test_claim_vs_ci", "no checks ran on this commit")

        if _TEST_NOUN.search(text) and _TEST_VERB.search(text) and not negated and not has_tests:
            add(unit, "tests_claim_no_test_files", "no test file changed")

    return tuple(found.values())


GENERIC_STEMS = frozenset(
    [
        "index",
        "page",
        "route",
        "layout",
        "main",
        "mod",
        "init",
        "__init__",
        "server",
        "handler",
        "utils",
        "types",
    ]
)
_PARTS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _named_by(name: str, words: set[str], flat: set[str]) -> bool:
    if len(_norm(name)) >= 3 and _norm(name) in flat:
        return True

    parts = [part.lower() for part in _PARTS.findall(name) if len(part) >= 3]

    return bool(parts) and all(
        part in words or part + "s" in words or part.removesuffix("s") in words for part in parts
    )


def _is_named(
    delta: Delta, tokens: tuple[str, ...], words: set[str], flat: set[str], idents: set[str]
) -> bool:
    path = PurePosixPath(delta.path)
    first = path.name.split(".")[0].lstrip("+").lower() or path.name.lower()

    names = [path.parent.name.strip("()")] if first in GENERIC_STEMS else [path.stem, path.name]

    return (
        any(hits(token, delta.path) for token in tokens)
        or any(name and _named_by(name, words, flat) for name in names)
        or any(symbol in idents for symbol in _DEFINED.findall(delta.diff))
    )


def _largest(files: Iterable[FileChange]) -> tuple[FileChange, ...]:
    return tuple(sorted(files, key=lambda f: (-(f.added + f.removed), f.path)))


def _manifest_lines(delta: Delta) -> tuple[str, ...]:
    added = (line[1:].strip() for line in delta.diff.splitlines() if line.startswith("+"))

    return tuple(line for line in added if line and not line.startswith("++"))[:MANIFEST_LINES]


def _pointers(files: tuple[FileChange, ...], deltas: dict[str, Delta]) -> tuple[Pointer, ...]:
    live = tuple(f for f in files if f.kind != "generated")
    sensitive = _largest(f for f in live if f.sensitive)
    groups: tuple[tuple[tuple[FileChange, ...], Callable[[FileChange], str]], ...] = (
        (
            tuple(f for f in sensitive if not f.named),
            lambda f: f"{f.sensitive}; its path is not in the description",
        ),
        (sensitive, lambda f: str(f.sensitive)),
        (
            _largest(f for f in live if f.kind == "code"),
            lambda f: f"largest code change (+{f.added} −{f.removed})",
        ),
    )
    out: list[Pointer] = []

    for members, reason in groups:
        for file in members:
            if len(out) < MAX_POINTERS and all(file.path != p.path for p in out):
                rule = sensitive_rule(file.path)
                lines = _manifest_lines(deltas[file.path]) if rule and rule.shows_added else ()
                out.append(Pointer(file.path, reason(file), lines))

    return tuple(out)


def _check_state(conclusion: str) -> CheckState:
    if conclusion in _FAILED:
        return "failed"

    return "passed" if conclusion in _PASSING else "pending"


def brief_of(
    pr: str, title: str, body: str, head_sha: str, deltas: tuple[Delta, ...],
    checks: tuple[Check, ...], known: frozenset[str],
) -> Brief:  # fmt: skip
    units = units_of(title, body)
    text = " ".join(_URL.sub(" ", unit.text) for unit in units)
    tokens = path_tokens(text)
    words = {word.lower() for word in re.findall(r"[A-Za-z0-9]+", text)}
    flat = {_norm(word) for word in re.findall(r"[\w.+-]+", text)}
    idents = set(re.findall(r"[A-Za-z_$][\w$]*", text))
    files = tuple(
        FileChange(
            d.path,
            kind_of(d),
            d.added,
            d.removed,
            _is_named(d, tokens, words, flat, idents),
            reason_of(d.path),
        )
        for d in sorted(deltas, key=lambda d: d.path)
    )
    mismatches = _mismatches(units, deltas, files, checks, Tree(known))

    return Brief(
        pr,
        title,
        head_sha,
        files,
        checks,
        mismatches,
        _pointers(files, {d.path: d for d in deltas}),
    )


def build_brief(acquisition: Acquisition, known: frozenset[str]) -> Brief:
    snapshot = acquisition.snapshot
    records = acquisition.records
    deltas = tuple(
        Delta(
            item.path,
            item.opaque,
            item.added_lines,
            item.removed_lines,
            records.get(f"diff:{item.path}", "").partition("\n")[2],
            records.get(f"head:{item.path}", ""),
        )
        for item in acquisition.inventory.items
    )
    latest: dict[str, tuple[tuple[float, int], str]] = {}

    for _, evidence in acquisition.evidence:
        if (
            evidence.subject_kind == "commit"
            and evidence.subject_sha == snapshot.comparison.head_sha
        ):
            rank = (evidence.completed_at, evidence.attempt)

            if evidence.name not in latest or rank >= latest[evidence.name][0]:
                latest[evidence.name] = (rank, evidence.conclusion)

    checks = tuple(
        Check(name, _check_state(conclusion)) for name, (_, conclusion) in sorted(latest.items())
    )
    metadata = acquisition.metadata

    return brief_of(
        f"{snapshot.comparison.repo}#{snapshot.comparison.pr_number}",
        metadata.title,
        metadata.body,
        snapshot.comparison.head_sha,
        deltas,
        checks,
        known,
    )

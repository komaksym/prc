"""Change map: the PR's changed symbols, how their calls moved, and a computed tour."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from prc.brief import Brief, Kind
from prc.snapshot import Acquisition

Language = Literal["python", "javascript", "typescript", "tsx"]
FileStatus = Literal["added", "modified", "deleted"]
SymbolKind = Literal["class", "function", "method"]
SymbolStatus = Literal["added", "modified", "deleted", "context"]
EdgeStatus = Literal["added", "removed", "kept"]
Resolution = Literal["exact", "name"]
LineOp = Literal["+", "-", " "]
StepKind = Literal["overview", "risky_file", "entry", "callee", "test", "summary"]


@dataclass(frozen=True, slots=True)
class DiffLine:
    op: LineOp
    old: int | None
    new: int | None
    text: str


@dataclass(frozen=True, slots=True)
class Hunk:
    old_start: int
    new_start: int
    lines: tuple[DiffLine, ...]


@dataclass(frozen=True, slots=True)
class FileNode:
    path: str
    kind: Kind
    status: FileStatus
    language: Language | None
    sensitive: str | None
    added: int
    removed: int
    hunks: tuple[Hunk, ...]
    symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Symbol:
    id: str
    path: str
    qualname: str
    kind: SymbolKind
    status: SymbolStatus
    span: tuple[int, int] | None
    base_span: tuple[int, int] | None
    added: int
    removed: int
    hunks: tuple[Hunk, ...]
    call_sites: int


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    status: EdgeStatus
    resolution: Resolution


@dataclass(frozen=True, slots=True)
class Step:
    kind: StepKind
    focus: tuple[str, ...]
    via: str | None


@dataclass(frozen=True, slots=True)
class ChangeMap:
    pr: str
    url: str | None
    title: str
    author: str
    base_sha: str
    head_sha: str
    brief: Brief
    files: tuple[FileNode, ...]
    symbols: tuple[Symbol, ...]
    edges: tuple[Edge, ...]
    tour: tuple[Step, ...]


def build_change_map(acquisition: Acquisition, repo: Path, brief: Brief) -> ChangeMap:
    raise NotImplementedError("M1 implements this; see PLANS.md Phase 3")

"""GraphDoc converter: goldens, integrity, limits, deltas and the D18 overview."""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

import pytest

from map_sample import large_map, shop_map
from prc.changemap import ChangeMap, Edge, Step, SymbolStatus
from prc.pipeline import _change_map_from_stored
from prc.presentation import graphdoc
from prc.presentation.graphdoc import (
    GROUPED_AT,
    MAX_BODY,
    MAX_EDGES,
    MAX_HEADING,
    MAX_LABEL,
    MAX_NODES,
    MAX_STEPS,
    groups_of,
    picked_steps,
    to_graph_doc,
    validate_contract,
)

DATA = Path(__file__).resolve().parent / "data" / "graphdoc"
ID = re.compile("^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


def stored(name: str) -> ChangeMap:
    return _change_map_from_stored(json.loads((DATA / "inputs" / (name + ".json")).read_text()))


def cases() -> dict[str, ChangeMap]:
    return {
        "shop": shop_map(),
        "librarysync-98": stored("librarysync-98"),
        "em-5756": stored("em-5756"),
        "swarm-116": stored("swarm-116"),
        "grouped": large_map(60),
    }


def canon(doc: object) -> str:
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def flood_map(status: SymbolStatus = "context", risky: bool = False) -> ChangeMap:
    base = shop_map()
    symbols = tuple(
        dataclasses.replace(
            base.symbols[0],
            id=f"pkg{i}/code.py::func_{i}",
            path=f"pkg{i}/code.py",
            qualname=f"func_{i}",
            status=status,
            added=300 - i,
            removed=0,
        )
        for i in range(300)
    )
    files = tuple(
        dataclasses.replace(base.files[2], path=s.path, symbols=(s.id,), sensitive=None)
        for s in symbols
    )
    return dataclasses.replace(
        base,
        symbols=symbols,
        files=files,
        edges=tuple(Edge(symbols[0].id, s.id, "added", "exact") for s in symbols[1:]),
        tour=(
            Step("overview", (), None),
            *((Step("risky_file", (f.path,), None) for f in files) if risky else ()),
            Step("entry", (symbols[-1].id,), None),
            Step("summary", (), None),
        ),
    )


def assert_bounded(change_map: ChangeMap) -> None:
    plotted = to_graph_doc(change_map)
    doc = plotted.doc
    assert validate_contract(doc) == ()
    assert len(doc["nodes"]) <= MAX_NODES
    assert len(doc["edges"]) <= MAX_EDGES
    assert len(doc["walkthrough"]["steps"]) <= MAX_STEPS
    assert plotted.dropped_symbols == len(change_map.symbols) - len(plotted.symbol_index)
    assert plotted.dropped_edges == len(change_map.edges) - len(doc["edges"])
    node_ids = {n["id"] for n in doc["nodes"]}
    assert {"s" + str(i) for i in plotted.symbol_index.values()} <= node_ids
    assert {"f" + str(i) for i in plotted.file_index.values()} <= node_ids
    assert plotted == to_graph_doc(change_map)


@pytest.mark.parametrize("status", ["context", "modified"])
@pytest.mark.parametrize("risky", [False, True])
def test_graphdoc_flood_terminates(status: str, risky: bool) -> None:
    code = (
        "from test_graphdoc import flood_map, assert_bounded; "
        f"assert_bounded(flood_map({status!r}, {risky!r}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src:tests"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("change_map", [shop_map(), large_map(60)])
def test_graphdoc_retains_ordinary_files(change_map: ChangeMap) -> None:
    plotted = to_graph_doc(change_map)
    symbols = {s.path for s in change_map.symbols}
    ordinary = {f.path: i for i, f in enumerate(change_map.files) if f.path not in symbols}
    assert ordinary.items() <= plotted.file_index.items()
    nodes = {n["id"]: n for n in plotted.doc["nodes"]}
    for path, i in ordinary.items():
        assert nodes["f" + str(i)]["files"][0]["path"] == path
    assert_bounded(change_map)


@pytest.mark.parametrize("status", ["context", "modified"])
def test_graphdoc_small_budget_prioritizes_risky_files(
    monkeypatch: pytest.MonkeyPatch, status: SymbolStatus
) -> None:
    monkeypatch.setattr(graphdoc, "MAX_NODES", 4)
    plotted = to_graph_doc(flood_map(status, risky=True))
    assert [n["id"] for n in plotted.doc["nodes"]] == ["f0", "f1", "f2", "f3"]
    assert plotted.symbol_index == {}
    assert plotted.file_index == {f"pkg{i}/code.py": i for i in range(4)}
    assert_bounded(flood_map(status, risky=True))


def test_graphdoc_file_only_flood_prioritizes_risky_target() -> None:
    base = flood_map(risky=True)
    change_map = dataclasses.replace(
        base, symbols=(), edges=(), tour=(Step("risky_file", (base.files[-1].path,), None),)
    )
    plotted = to_graph_doc(change_map)
    assert base.files[-1].path in plotted.file_index
    assert len(plotted.doc["nodes"]) == MAX_NODES
    assert_bounded(change_map)


@pytest.mark.parametrize(
    "status, partial", [("context", False), ("context", True), ("modified", True)]
)
def test_graphdoc_omitted_focus_is_named(status: SymbolStatus, partial: bool) -> None:
    base = flood_map(status)
    refs = ((base.symbols[0].id,) if partial else ()) + (base.symbols[-1].id,)
    change_map = dataclasses.replace(base, tour=(Step("entry", refs, None),))
    if status == "modified":
        refs = tuple(s.id for s in base.symbols)
        change_map = dataclasses.replace(base, tour=(Step("entry", refs, None),))
    plotted = to_graph_doc(change_map)
    step = plotted.doc["walkthrough"]["steps"][1]
    assert "not shown" in step["body"].lower()
    if status == "context":
        assert "func_299" in step["body"]
        assert step["focus"]["kind"] == ("selection" if partial else "all")
    else:
        assert "func_256" in step["body"]
    assert len(step["body"]) <= MAX_BODY
    assert_bounded(change_map)


def test_graphdoc_long_body_preserves_omitted_focus_name() -> None:
    base = flood_map()
    last = dataclasses.replace(
        base.symbols[-1], path="long/" + "x" * 150 + ".py", qualname="missing_target"
    )
    last = dataclasses.replace(last, id=last.path + "::" + last.qualname)
    change_map = dataclasses.replace(
        base, symbols=base.symbols[:-1] + (last,), tour=(Step("entry", (last.id,), None),)
    )
    body = to_graph_doc(change_map).doc["walkthrough"]["steps"][1]["body"]
    assert "missing_target" in body and "not shown" in body.lower()
    assert len(body) <= MAX_BODY


def test_graphdoc_grouped_drop_counts_are_exact() -> None:
    change_map = large_map(60)
    plotted = to_graph_doc(change_map)
    assert 0 < len(plotted.doc["edges"]) < len(change_map.edges)
    assert_bounded(change_map)


def test_graphdoc_matches_goldens() -> None:
    for name, change_map in cases().items():
        assert (DATA / (name + ".json")).read_text() == canon(to_graph_doc(change_map).doc), name


def test_graphdoc_ids_and_integrity() -> None:
    for _name, change_map in cases().items():
        plotted = to_graph_doc(change_map)
        doc = plotted.doc
        assert validate_contract(doc) == ()
        node_ids = [node["id"] for node in doc["nodes"]]
        assert len(set(node_ids)) == len(node_ids)
        for nid in node_ids:
            assert ID.match(nid) is not None
        for node in doc["nodes"]:
            if node["id"].startswith("s"):
                assert change_map.symbols[int(node["id"][1:])].id
            elif node["id"].startswith("f"):
                assert change_map.files[int(node["id"][1:])].path
            else:
                assert node["id"].startswith("g"), node["id"]
        for edge in doc["edges"]:
            assert edge["id"].startswith("e")
            assert change_map.edges[int(edge["id"][1:])]
            assert edge["from"] in node_ids and edge["to"] in node_ids
        for n, step in enumerate(doc["walkthrough"]["steps"]):
            assert step["id"] == "w" + str(n)
            focus = step["focus"]
            if focus["kind"] == "selection":
                assert focus["nodes"]
                assert all(ref in node_ids for ref in focus["nodes"])
        for sid in plotted.symbol_index:
            assert "s" + str(plotted.symbol_index[sid]) in node_ids


def big_map() -> ChangeMap:
    base = shop_map()
    symbols = list(base.symbols)
    edges = list(base.edges)
    base_ids = [s.id for s in symbols]
    for i in range(33):
        sid = "src/steady/file" + str(i % 2) + ".py::steady_" + str(i)
        symbols.append(
            dataclasses.replace(
                symbols[2],
                id=sid,
                path="src/steady/file" + str(i % 2) + ".py",
                qualname="steady_" + str(i),
            )
        )
    for i in range(260):
        sid = "src/context/bulk" + str(i % 3) + ".py::bulk_" + str(i)
        symbols.append(
            dataclasses.replace(
                symbols[0],
                id=sid,
                path="src/context/bulk" + str(i % 3) + ".py",
                qualname="bulk_" + str(i),
                status="context",
                span=(1, 2),
                base_span=(1, 2),
            )
        )
    symbols = sorted(symbols, key=lambda s: s.id)
    for i in range(30):
        sid = "zzz/cold.py::cold_" + str(i)
        symbols.append(
            dataclasses.replace(
                symbols[0],
                id=sid,
                path="zzz/cold.py",
                qualname="cold_" + str(i),
                status="context",
                span=(1, 2),
                base_span=(1, 2),
            )
        )
    symbols = sorted(symbols, key=lambda s: s.id)
    at = {s.id for s in symbols}
    statuses: tuple[Literal["added", "removed", "kept"], ...] = ("added", "removed", "kept")
    for i in range(2000):
        source = sorted(at)[i % len(at)]
        target = sorted(at)[(i * 7 + 3) % len(at)]
        if source == target:
            continue
        edges.append(Edge(source, target, statuses[i % 3], ("exact", "name")[i % 5 == 0]))
    tour = (
        (Step("overview", (), None),)
        + tuple(Step("entry", (sid,), None) for sid in base_ids[:20])
        + (Step("summary", (), None),)
    )
    seen: dict[str, list[str]] = {}
    for sym in symbols:
        seen.setdefault(sym.path, []).append(sym.id)
    files = list(base.files) + [
        dataclasses.replace(base.files[2], path=path, symbols=tuple(sorted(ids)))
        for path, ids in sorted(seen.items())
        if path not in {f.path for f in base.files}
    ]
    return dataclasses.replace(
        base, files=tuple(files), symbols=tuple(symbols), edges=tuple(edges), tour=tour
    )


def test_graphdoc_limits() -> None:
    change_map = big_map()
    assert len(change_map.symbols) == 336 and len(change_map.edges) > 512
    assert sum(s.status != "context" for s in change_map.symbols) <= GROUPED_AT
    plotted = to_graph_doc(change_map)
    doc = plotted.doc
    assert validate_contract(doc) == ()
    assert len(doc["nodes"]) <= MAX_NODES
    assert len(doc["edges"]) <= MAX_EDGES
    assert len(doc["walkthrough"]["steps"]) <= MAX_STEPS
    for node in doc["nodes"]:
        assert len(node["label"]) <= MAX_LABEL
    for step in doc["walkthrough"]["steps"]:
        assert 1 <= len(step["heading"]) <= MAX_HEADING
        assert 1 <= len(step["body"]) <= MAX_BODY
    assert len(plotted.symbol_index) == MAX_NODES
    assert plotted.dropped_symbols == len(change_map.symbols) - len(plotted.symbol_index)
    assert plotted.dropped_edges == len(change_map.edges) - len(doc["edges"])


def test_graphdoc_no_symbols_uses_file_nodes() -> None:
    plotted = to_graph_doc(stored("swarm-116"))
    doc = plotted.doc
    assert [node["id"] for node in doc["nodes"]] == ["f" + str(i) for i in range(7)]
    assert [lane["id"] for lane in doc["lanes"]] == ["files"]
    assert len(doc["walkthrough"]["steps"]) >= 2


def test_graphdoc_risky_steps_focus_file_nodes() -> None:
    change_map = stored("em-5756")
    plotted = to_graph_doc(change_map)
    doc = plotted.doc
    node_ids = [node["id"] for node in doc["nodes"]]
    risky = [s for s in picked_steps(change_map) if s is not None and s.kind == "risky_file"]
    assert len(risky) == 2
    focuses = [s["focus"] for s in doc["walkthrough"]["steps"][1:3]]
    assert focuses
    for focus in focuses:
        assert focus["kind"] == "selection"
        assert focus["nodes"] and all(n.startswith("f") for n in focus["nodes"])
        assert all(n in node_ids for n in focus["nodes"])


def test_graphdoc_delta_and_emphasis() -> None:
    plotted = to_graph_doc(shop_map())
    doc = plotted.doc
    by_symbol = {s.id: s for s in shop_map().symbols}
    want = {"added": "added", "modified": "modified", "deleted": "removed", "context": "unchanged"}
    for node in doc["nodes"]:
        for ref in node["files"]:
            assert ref["revision"] == ("base" if node["delta"] == "removed" else "head")
        if node["id"].startswith("s"):
            sym = by_symbol[shop_map().symbols[int(node["id"][1:])].id]
            assert node["delta"] == want[sym.status]
    for edge in doc["edges"]:
        assert edge["animated"] is False
        raw = shop_map().edges[int(edge["id"][1:])]
        assert (
            edge["delta"]
            == {"added": "added", "removed": "removed", "kept": "unchanged"}[raw.status]
        )
        if raw.status == "removed":
            assert edge["emphasis"] == "muted"
        if raw.resolution == "name":
            assert edge["emphasis"] == "muted" and edge["label"] == "name-only"
    heroes = [edge for edge in doc["edges"] if edge["emphasis"] == "hero"]
    assert [edge["id"] for edge in heroes] == ["e1"]
    raw = shop_map().edges[int(heroes[0]["id"][1:])]
    assert (raw.status, raw.resolution) == ("added", "exact")
    walk: set[str] = set()
    for step in picked_steps(shop_map()):
        if step is not None:
            walk.update(step.focus)
            if step.via is not None:
                walk.add(step.via)
    assert raw.source in walk and raw.target in walk


def scattered_map() -> ChangeMap:
    base = shop_map()
    extra = []
    paths: dict[str, list[str]] = {}
    for i in range(40):
        sid = "src/big/m" + str(i // 4) + ".py::big_func_" + str(i)
        path, qualname = sid.split("::", 1)
        extra.append(
            dataclasses.replace(
                base.symbols[2],
                id=sid,
                path=path,
                qualname=qualname,
                status="modified",
                span=(1, 2),
                base_span=(1, 2),
            )
        )
        paths.setdefault(path, []).append(sid)
    sid = "lonely/only.py::solo"
    extra.append(
        dataclasses.replace(base.symbols[2], id=sid, path="lonely/only.py", qualname="solo")
    )
    paths.setdefault("lonely/only.py", []).append(sid)
    files = base.files + tuple(
        dataclasses.replace(base.files[2], path=path, symbols=tuple(sorted(ids)))
        for path, ids in sorted(paths.items())
    )
    symbols = tuple(sorted(base.symbols + tuple(extra), key=lambda s: s.id))
    return dataclasses.replace(base, files=files, symbols=symbols)


def test_graphdoc_large_pr_groups() -> None:
    change_map = scattered_map()
    changed = [s for s in change_map.symbols if s.status != "context"]
    assert len(changed) > GROUPED_AT
    groups = groups_of(change_map)
    assert len(groups) > 1
    assert [g.label for g in groups] == sorted(g.label for g in groups)
    plotted = to_graph_doc(change_map)
    doc = plotted.doc
    assert validate_contract(doc) == ()
    node_ids = [node["id"] for node in doc["nodes"]]
    assert node_ids[: len(groups)] == ["g" + str(i) for i in range(len(groups))]
    by_id = {s.id: s for s in change_map.symbols}
    for n, group in enumerate(groups):
        node = doc["nodes"][n]
        total = group.added + group.modified + group.deleted
        assert node["subtitle"] == (
            str(total)
            + " changed: "
            + str(group.added)
            + " added, "
            + str(group.modified)
            + " modified, "
            + str(group.deleted)
            + " deleted"
        )
        assert total == len(group.members)
        assert group.added == sum(by_id[sid].status == "added" for sid in group.members)
        assert group.modified == sum(by_id[sid].status == "modified" for sid in group.members)
        assert group.deleted == sum(by_id[sid].status == "deleted" for sid in group.members)
        if group.tests:
            assert any("test" in badge for badge in node["badges"])
        for sid in group.members:
            assert by_id[sid].status != "context"
    walk_symbols: set[str] = set()
    for step in picked_steps(change_map):
        if step is not None and step.kind in ("entry", "callee", "test"):
            walk_symbols.update(step.focus)
            if step.via is not None:
                walk_symbols.add(step.via)
    for sid in walk_symbols:
        if sid in by_id:
            assert sid in plotted.symbol_index
    assert len(doc["nodes"]) <= len(groups) + len(plotted.symbol_index) + len(plotted.file_index)
    for node in doc["nodes"]:
        if node["id"].startswith("s"):
            assert by_id[change_map.symbols[int(node["id"][1:])].id].status != "context"


def test_prlens_lock_matches_bundle_and_goldens() -> None:
    import hashlib
    from importlib.resources import files

    assets = files("prc.presentation") / "map_assets"
    lock = json.loads((assets / "prlens.lock.json").read_text())
    assert (lock["renderer"], lock["schema"]) == ("0.3.2", "0.7.0")
    bundle = (assets / "prlens.bundle.js").read_bytes()
    assert hashlib.sha256(bundle).hexdigest() == lock["bundle_sha256"]
    assert len(bundle) < 100 * 1024
    goldens = sorted(p.name for p in DATA.glob("*.json"))
    assert goldens and sorted(lock["validated_goldens"]) == goldens
    for name in goldens:
        digest = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
        assert lock["validated_goldens"][name] == digest, name


def test_graphdoc_grouping_threshold_and_membership() -> None:
    assert groups_of(shop_map()) == ()
    assert groups_of(large_map(32)) == ()
    assert groups_of(large_map(33))
    change_map = large_map(60)
    groups = groups_of(change_map)
    assert {g.label for g in groups} == {"src/pkg", "tests"}
    members = [sid for group in groups for sid in group.members]
    assert len(members) == len(set(members))
    assert set(members) == {s.id for s in change_map.symbols if s.status != "context"}
    assert (
        groups_of(
            dataclasses.replace(
                change_map,
                symbols=tuple(reversed(change_map.symbols)),
                files=tuple(reversed(change_map.files)),
            )
        )
        == groups
    )
    by_id = {s.id: s for s in change_map.symbols}
    kinds = {f.path: f.kind for f in change_map.files}
    for group in groups:
        assert group.tests == sum(kinds[by_id[sid].path] == "test" for sid in group.members)
    scattered = {g.label: g for g in groups_of(scattered_map())}
    assert scattered["src/big"].is_dir
    assert len(scattered["src/big"].members) == 40
    assert not scattered["lonely/only.py"].is_dir
    assert scattered["lonely/only.py"].members == ("lonely/only.py::solo",)
    assert scattered["src/shop"].is_dir
    assert not scattered["web/src/cart.ts"].is_dir


def test_graphdoc_grouped_overview_obeys_node_cap() -> None:
    base = large_map(60)
    symbols = tuple(
        dataclasses.replace(
            base.symbols[0],
            id=f"pkg{i}/code.py::f",
            path=f"pkg{i}/code.py",
            qualname="f",
            status="modified",
            span=(1, 3),
            base_span=(1, 3),
        )
        for i in range(300)
    )
    files = tuple(
        dataclasses.replace(base.files[0], path=s.path, symbols=(s.id,), sensitive=None)
        for s in symbols
    )
    change_map = dataclasses.replace(
        base,
        symbols=symbols,
        files=files,
        edges=(),
        tour=(
            Step("overview", (), None),
            Step("entry", (symbols[0].id,), None),
            Step("summary", (), None),
        ),
    )
    plotted = to_graph_doc(change_map)
    assert len(plotted.doc["nodes"]) == MAX_NODES
    assert plotted.symbol_index == {symbols[0].id: 0}
    assert plotted.dropped_symbols == 299
    assert validate_contract(plotted.doc) == ()


def test_graphdoc_many_context_files_obey_node_cap() -> None:
    base = shop_map()
    symbols = tuple(
        dataclasses.replace(
            base.symbols[0],
            id=f"context/m{i}.py::f",
            path=f"context/m{i}.py",
            qualname="f",
            status="context",
            span=(1, 3),
            base_span=(1, 3),
        )
        for i in range(300)
    )
    files = tuple(
        dataclasses.replace(base.files[2], path=s.path, symbols=(s.id,), sensitive=None)
        for s in symbols
    )
    change_map = dataclasses.replace(base, symbols=base.symbols + symbols, files=base.files + files)
    plotted = to_graph_doc(change_map)
    assert len(plotted.doc["nodes"]) == MAX_NODES
    assert all(s.id in plotted.symbol_index for s in base.symbols if s.status != "context")
    assert plotted.dropped_symbols == len(change_map.symbols) - len(plotted.symbol_index)
    assert validate_contract(plotted.doc) == ()


def test_board_coverage_states_changed_file_budget() -> None:
    from prc.explainer.boards import coverage

    change_map = {
        "files": [
            {"path": "a.py", "kind": "code", "added": 2},
            {"path": "b.py", "kind": "code", "added": 5},
        ],
        "brief": {
            "files": [
                {"path": "a.py", "kind": "code"},
                {"path": "b.py", "kind": "code"},
            ]
        },
        "symbols": [
            {
                "id": "a.py::f",
                "path": "a.py",
                "status": "modified",
                "span": [1, 10],
                "base_span": [1, 10],
            },
            {
                "id": "b.py::g",
                "path": "b.py",
                "status": "added",
                "span": [1, 4],
                "base_span": None,
            },
        ],
        "tour": [{"kind": "entry", "focus": ["a.py::f"]}],
    }
    board = {
        "name": "budget",
        "scenes": [{"type": "list", "cite": [{"line": "a.py:3"}]}],
    }

    out = coverage(board, change_map)

    assert "covers 1 of 2 changed files" in out
    assert "files 1/2" in out

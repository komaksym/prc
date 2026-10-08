"""Cards use every supported receipt shape and preserve file status."""

from __future__ import annotations

from typing import Any

import pytest

from prc.explainer.check import verify_board
from prc.presentation import card


def _sym(
    sid: str,
    path: str,
    span: list[int],
    base_span: list[int] | None = None,
    added: int = 1,
    removed: int = 0,
) -> dict[str, Any]:
    return {
        "id": sid,
        "path": path,
        "qualname": sid.rsplit("::", 1)[-1],
        "status": "modified",
        "span": span,
        "base_span": base_span if base_span is not None else list(span),
        "added": added,
        "removed": removed,
        "call_sites": 0,
    }


def _map(
    symbols: list[dict[str, Any]],
    brief_files: list[dict[str, Any]],
    map_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "pr": "acme/demo#1",
        "title": "Demo",
        "head_sha": "b" * 40,
        "symbols": symbols,
        "edges": [],
        "files": map_files if map_files is not None else [],
        "brief": {"files": brief_files, "checks": []},
    }


def test_quoted_files_covers_list_and_receipt_lines() -> None:
    board = {
        "scenes": [
            {
                "type": "list",
                "items": [
                    {"text": "a", "cite": "src/list_only/files.py:34"},
                    {"text": "b", "cite": "src/list_only/model.py:97"},
                ],
            },
            {
                "type": "receipt",
                "rows": [
                    {"line": "src/receipt_only/util.py:12", "text": "x"},
                ],
            },
            {"type": "groups", "cite": [{"line": "src/scene/a.py:1", "match": "x"}]},
            {"type": "diff", "file": "src/diff/b.py", "lines": ["5"]},
        ]
    }
    got = card.quoted_files(board)
    assert "src/list_only/files.py" in got
    assert "src/list_only/model.py" in got
    assert "src/receipt_only/util.py" in got
    assert "src/scene/a.py" in got
    assert "src/diff/b.py" in got


def test_quoted_files_skips_rows_without_lines_and_bad_cites() -> None:
    board = {
        "scenes": [
            {
                "type": "receipt",
                "rows": [
                    {"symbol": "src/a.py::f"},
                    {"edge": ["a", "b"]},
                    {"text": "no line key"},
                ],
            },
            {"type": "groups", "cite": [{"match": "x"}, "nope", {"line": ""}]},
            {"type": "list", "items": [{"text": "missing cite"}]},
        ]
    }
    assert card.quoted_files(board) == frozenset()
    assert card.cited_symbol_ids([], board) == []


def test_cited_ids_cover_list_receipt_and_cue_lines() -> None:
    sym_list = _sym("src/m.py::a", "src/m.py", [90, 100])
    sym_receipt = _sym("src/r.py::b", "src/r.py", [25, 35])
    sym_cue = _sym("src/c.py::c", "src/c.py", [2000, 2010], [1018, 1018])
    board = {
        "scenes": [
            {"type": "list", "items": [{"text": "a", "cite": "src/m.py:97"}]},
            {"type": "receipt", "rows": [{"line": "src/r.py:30", "text": "x"}]},
            {
                "type": "diff",
                "file": "src/c.py",
                "lines": [{"ref": "1030", "step": 1}],
                "cues": [{"at": "old", "do": "note", "line": "-1018", "text": "x"}],
            },
        ]
    }
    got = card.cited_symbol_ids([sym_list, sym_receipt, sym_cue], board)
    assert got == ["src/c.py::c", "src/m.py::a", "src/r.py::b"]


def test_cited_ids_negative_ref_matches_base_span_only() -> None:
    sym = _sym("src/n.py::f", "src/n.py", [10, 20], [1010, 1020])
    one = {"scenes": [{"type": "groups", "cite": [{"line": "src/n.py:-1015", "match": "x"}]}]}
    assert card.cited_symbol_ids([sym], one) == [sym["id"]]
    two = {"scenes": [{"type": "groups", "cite": [{"line": "src/n.py:15", "match": "x"}]}]}
    assert card.cited_symbol_ids([sym], two) == [sym["id"]]
    three = {"scenes": [{"type": "groups", "cite": [{"line": "src/n.py:1015", "match": "x"}]}]}
    assert card.cited_symbol_ids([sym], three) == []
    four = {"scenes": [{"type": "groups", "cite": [{"line": "src/n.py:-15", "match": "x"}]}]}
    assert card.cited_symbol_ids([sym], four) == []


def test_look_first_ranks_list_cited_symbol_first() -> None:
    cited = _sym("src/cited.py::small", "src/cited.py", [95, 99], added=1, removed=0)
    busy = _sym("src/busy.py::big", "src/busy.py", [1, 10], added=100, removed=50)
    m = _map(
        [cited, busy],
        [{"path": "src/cited.py", "kind": "code"}, {"path": "src/busy.py", "kind": "code"}],
    )
    board = {"scenes": [{"type": "list", "items": [{"text": "x", "cite": "src/cited.py:97"}]}]}
    assert "src/cited.py" in card.quoted_files(board)
    assert card.cited_symbol_ids([cited, busy], board) == [cited["id"]]
    got = card.look_first(m, None, 2, board)
    assert [e.id for e in got] == [cited["id"], busy["id"]]


def test_look_first_prioritizes_displayed_change_over_context_receipt() -> None:
    context = _sym("src/sync.py::plan_events", "src/sync.py", [10, 20])
    change = _sym("src/sync.py::reconcile", "src/sync.py", [30, 60])
    m = _map([context, change], [{"path": "src/sync.py", "kind": "code"}])
    board = {
        "scenes": [
            {"type": "groups", "cite": [{"line": "src/sync.py:12", "match": "event"}]},
            {"type": "diff", "file": "src/sync.py", "lines": ["30", "45"]},
        ]
    }
    assert [entry.id for entry in card.look_first(m, board=board)] == [change["id"], context["id"]]


@pytest.mark.parametrize("ref", ["1", "-101"])
def test_top_level_displayed_line_gets_fallback_with_changed_neighbors(ref: str) -> None:
    path = "src/a.py"
    neighbors = [
        _sym(f"{path}::context", path, [10, 20], [110, 120]),
        _sym(f"{path}::other", path, [30, 40], [130, 140]),
    ]
    m = _map(
        neighbors,
        [{"path": path, "kind": "code"}],
        [
            {
                "path": path,
                "status": "modified",
                "hunks": [
                    {
                        "lines": [
                            {"op": "-", "old": 101, "new": None, "text": "API = 1"},
                            {"op": "+", "old": None, "new": 1, "text": "API = 2"},
                        ]
                    }
                ],
            }
        ],
    )
    board = {
        "scenes": [
            {
                "type": "diff",
                "file": path,
                "lines": [ref],
                "cues": [{"at": 0, "do": "step", "n": 1}],
            }
        ]
    }
    assert verify_board(board, m)["receipts"] == 1
    entries = card.look_first(m, board=board)
    assert [entry.id for entry in entries] == [f"file:{path}", *[s["id"] for s in neighbors]]
    assert entries[0].status == "modified"


@pytest.mark.parametrize("kind", ["symbol", "edge"])
def test_explicit_receipt_ranks_changed_symbols(kind: str) -> None:
    path = "src/a.py"
    busy = [_sym(f"{path}::busy{i}", path, [10, 20], added=100) for i in range(3)]
    cited = _sym(f"{path}::cited", path, [30, 40])
    target = _sym("src/b.py::target", "src/b.py", [50, 60])
    m = _map(
        [*busy, cited, target],
        [
            {"path": path, "kind": "code"},
            {"path": "src/b.py", "kind": "code"},
        ],
    )
    m["edges"] = [{"source": cited["id"], "target": target["id"], "status": "added"}]
    row = {"symbol": cited["id"]} if kind == "symbol" else {"edge": [cited["id"], target["id"]]}
    board = {
        "scenes": [
            {
                "type": "receipt",
                "rows": [row],
                "cues": [{"at": 0, "do": "rows"}],
            }
        ]
    }
    assert verify_board(board, m)["receipts"] == 1
    expected = [cited["id"]] if kind == "symbol" else [cited["id"], target["id"]]
    assert card.cited_symbol_ids(m["symbols"], board) == expected
    assert [entry.id for entry in card.look_first(m, board=board)][: len(expected)] == expected
    assert all(not entry.id.startswith("file:") for entry in card.look_first(m, board=board))


def test_diff_context_cites_follow_displayed_lines_across_scenes() -> None:
    path = "src/a.py"
    context = _sym(f"{path}::context", path, [10, 20])
    displayed = _sym(f"{path}::displayed", path, [30, 40])
    later = _sym(f"{path}::later", path, [50, 60])
    m = _map(
        [context, displayed, later],
        [{"path": path, "kind": "code"}],
        [
            {
                "path": path,
                "hunks": [
                    {
                        "lines": [
                            {"op": "+", "old": None, "new": n, "text": "change"}
                            for n in [10, 30, 50]
                        ]
                    }
                ],
            },
        ],
    )
    board = {
        "scenes": [
            {
                "type": "diff",
                "file": path,
                "lines": ["30"],
                "cite": [{"line": f"{path}:10", "match": "change"}],
                "cues": [{"at": 0, "do": "step", "n": 1}],
            },
            {
                "type": "diff",
                "file": path,
                "lines": [{"ref": "50", "step": 1}],
                "cues": [{"at": 0, "do": "step", "n": 1}],
            },
        ]
    }
    assert verify_board(board, m)["receipts"] == 3
    expected = [displayed["id"], later["id"], context["id"]]
    assert card.cited_symbol_ids(m["symbols"], board) == expected
    assert [entry.id for entry in card.look_first(m, board=board)] == expected


@pytest.mark.parametrize("ref", ["15", "-115"])
def test_displayed_line_inside_changed_symbol_has_no_file_fallback(ref: str) -> None:
    sym = _sym("src/a.py::f", "src/a.py", [10, 20], [110, 120])
    m = _map([sym], [{"path": "src/a.py", "kind": "code"}])
    board = {"scenes": [{"type": "diff", "file": "src/a.py", "lines": [ref]}]}
    assert [entry.id for entry in card.look_first(m, board=board)] == [sym["id"]]


def test_mixed_receipts_keep_context_order_and_ignore_ineligible_symbols() -> None:
    busy = _sym("src/a.py::busy", "src/a.py", [10, 20], added=100)
    cited = _sym("src/a.py::cited", "src/a.py", [30, 40])
    later = _sym("src/b.py::later", "src/b.py", [50, 60])
    unchanged = _sym("src/b.py::unchanged", "src/b.py", [70, 80])
    unchanged["status"] = "unchanged"
    test = _sym("tests/test_a.py::test_f", "tests/test_a.py", [1, 10])
    m = _map(
        [busy, cited, later, unchanged, test],
        [
            {"path": "src/a.py", "kind": "code"},
            {"path": "src/b.py", "kind": "code"},
            {"path": "tests/test_a.py", "kind": "test"},
        ],
    )
    board = {
        "scenes": [
            {
                "type": "receipt",
                "rows": [
                    {"symbol": "src/missing.py::missing"},
                    {"symbol": unchanged["id"]},
                    {"edge": [test["id"], cited["id"]]},
                    {"symbol": cited["id"]},
                ],
            },
            {"type": "list", "items": [{"text": "later", "cite": "src/b.py:55"}]},
        ]
    }
    assert [entry.id for entry in card.look_first(m, board=board)] == [
        cited["id"],
        later["id"],
        busy["id"],
    ]


def test_look_first_fallback_for_list_quoted_file_without_symbols() -> None:
    m = _map(
        [],
        [{"path": "src/files.py", "kind": "code"}],
        [{"path": "src/files.py", "status": "modified"}],
    )
    board = {"scenes": [{"type": "list", "items": [{"text": "x", "cite": "src/files.py:34"}]}]}
    got = card.look_first(m, None, 3, board)
    assert [e.id for e in got] == ["file:src/files.py"]


@pytest.mark.parametrize(
    ("map_status", "want"),
    [("added", "added"), ("deleted", "deleted"), (None, "modified"), ("missing", "modified")],
)
def test_file_fallback_uses_map_file_status(map_status: Any, want: str) -> None:
    brief_files = [{"path": "src/top.py", "kind": "code"}]
    map_files: list[dict[str, Any]] = (
        [] if map_status == "missing" else [{"path": "src/top.py", "status": map_status}]
    )
    m = _map([], brief_files, map_files)
    board = {"scenes": [{"type": "diff", "file": "src/top.py", "lines": ["1"]}]}
    got = card.look_first(m, None, 3, board)
    assert len(got) == 1
    assert got[0].id == "file:src/top.py"
    assert got[0].status == want


def test_hidden_risk_suffix_escapes_html() -> None:
    reasons = ["reason-a", "reason-b", "reason-c", "<script>alert(1)</script>"]
    brief_files = [
        {"path": "src/r" + str(i) + ".py", "kind": "code", "sensitive": reason}
        for i, reason in enumerate(reasons)
    ]
    m = _map([], brief_files)
    html = card.build_card_html(m)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_look_first_groups_order_cited_quoted_unquoted() -> None:
    cited = _sym("src/a.py::cited", "src/a.py", [95, 99])
    quoted = _sym("src/b.py::quoted", "src/b.py", [1, 10], added=5, removed=5)
    plain = _sym("src/c.py::plain", "src/c.py", [1, 10], added=50, removed=50)
    m = _map(
        [plain, quoted, cited],
        [
            {"path": "src/a.py", "kind": "code"},
            {"path": "src/b.py", "kind": "code"},
            {"path": "src/c.py", "kind": "code"},
        ],
    )
    board = {
        "scenes": [
            {"type": "list", "items": [{"text": "x", "cite": "src/a.py:97"}]},
            {"type": "diff", "file": "src/b.py", "lines": ["999"]},
        ]
    }
    got = card.look_first(m, None, 4, board)
    assert [e.id for e in got] == [cited["id"], "file:src/b.py", quoted["id"], plain["id"]]

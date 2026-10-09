from __future__ import annotations

import json
from pathlib import Path

import pytest

from prc.brief import Delta, kind_of, sensitive_rule
from prc.codegraph import parse_file
from prc.facts import compute_facts
from prc.identity import to_jsonable
from prc.presentation.card import build_card_html, untested
from prc.presentation.comment import render_comment
from test_changemap import by_id, custom_map


def test_unsupported_language_reports_limits_instead_of_no_changes(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"main.go": b"package main\nfunc run() { old() }\n"},
        {"main.go": b"package main\nfunc run() { next() }\n"},
    )
    data = to_jsonable(change)
    text = render_comment(data)
    html = build_card_html(data)

    assert "No code symbols changed" not in text + html
    assert "unsupported" in (text + html).lower()
    assert "parsed symbols changed" in html
    assert "main.go" in text
    assert "```mermaid" not in text
    assert (change.files[0].added, change.files[0].removed) == (1, 1)
    board = {"scenes": [{"type": "diff", "file": "main.go", "lines": ["2"]}]}
    quoted = build_card_html(data, board=board)
    assert "file-level change" in quoted
    assert "top-level change" not in quoted


def test_object_handlers_have_distinct_names_and_own_their_calls() -> None:
    parsed = parse_file(
        "handlers.ts",
        b"function helper() {}\n"
        b"const first = { run: () => helper(), method() { helper(); } };\n"
        b"const second = { run: function () { helper(); } };\n",
    )
    assert parsed is not None
    names = {definition.qualname for definition in parsed.definitions}

    assert {"first.run", "first.method", "second.run"} <= names
    assert {call.scope for call in parsed.calls} == {"first.run", "first.method", "second.run"}


def test_nested_handlers_keep_names_through_typescript_satisfies() -> None:
    parsed = parse_file(
        "command.ts",
        b"const command = { nested: { done: () => act() }, exec: () => act() } satisfies Command;\n",
    )
    assert parsed is not None
    assert {d.qualname for d in parsed.definitions} == {"command.nested.done", "command.exec"}


def test_large_browser_test_file_keeps_its_test_classification() -> None:
    assert kind_of(Delta("src/e2e/puppeteer/__tests__/commandCenter.ts", True, 5, 1)) == "test"


@pytest.mark.parametrize("path", [".puppeteer/keyboard.ts", "e2e/keyboard.ts"])
def test_browser_test_roots_count_as_test_files(path: str) -> None:
    assert kind_of(Delta(path, False, 1, 0)) == "test"


@pytest.mark.parametrize("path", ["yarn.lock", ".yarn/patches/react.patch", "uv.lock"])
def test_dependency_locks_and_patches_need_review(path: str) -> None:
    assert sensitive_rule(path) is not None


def test_large_text_files_keep_exact_line_counts(tmp_path: Path) -> None:
    unchanged = b"same long documentation line\n" * 2500
    change = custom_map(
        tmp_path,
        {"README.md": unchanged + b"old ending\n"},
        {"README.md": unchanged + b"new ending\nsecond ending\n"},
    )
    file = change.files[0]

    assert (file.added, file.removed) == (2, 1)
    assert file.symbols == ()


def test_line_counts_include_content_that_looks_like_diff_headers(tmp_path: Path) -> None:
    change = custom_map(tmp_path, {}, {"README.md": b"++ heading\n-- heading\n"})
    assert (change.files[0].added, change.files[0].removed) == (2, 0)


def test_repeated_decorator_does_not_make_unchanged_function_modified(tmp_path: Path) -> None:
    prefix = b"# retained context\n" * 210
    base = prefix + b"@pytest.mark.asyncio\nasync def existing():\n    return 1\n"
    head = (
        prefix
        + b"@pytest.mark.asyncio\nasync def inserted():\n    return existing()\n\n\n"
        + base[len(prefix) :]
    )
    symbols = by_id(custom_map(tmp_path, {"tests/test_m.py": base}, {"tests/test_m.py": head}))

    assert symbols["tests/test_m.py::existing"].status == "context"
    assert (
        symbols["tests/test_m.py::existing"].added,
        symbols["tests/test_m.py::existing"].removed,
    ) == (0, 0)
    assert symbols["tests/test_m.py::inserted"].status == "added"


def test_actual_decorator_change_still_changes_the_function(tmp_path: Path) -> None:
    change = custom_map(
        tmp_path,
        {"m.py": b"def run():\n    return 1\n"},
        {"m.py": b"@deco\ndef run():\n    return 1\n"},
    )
    assert by_id(change)["m.py::run"].status == "modified"


def test_librarysync_decorator_attribution_matches_original_revision(tmp_path: Path) -> None:
    case = json.loads(
        (Path(__file__).parent / "data/trustworthiness/librarysync-decorator.json").read_text()
    )
    change = custom_map(
        tmp_path, {case["path"]: case["base"].encode()}, {case["path"]: case["head"].encode()}
    )
    sid = (
        case["path"]
        + "::test_mark_next_episode_watched_creates_watched_event_and_internal_outbox_job"
    )
    existing = by_id(change).get(sid)
    assert existing is None or existing.status == "context"


def test_removed_test_call_is_not_live_test_evidence() -> None:
    data = {
        "brief": {"files": [{"path": "tests/test_m.py", "kind": "test"}]},
        "symbols": [
            {"id": "m.py::run", "qualname": "run", "path": "m.py", "status": "modified"},
            {
                "id": "tests/test_m.py::test_run",
                "qualname": "test_run",
                "path": "tests/test_m.py",
                "status": "deleted",
            },
        ],
        "edges": [
            {"source": "tests/test_m.py::test_run", "target": "m.py::run", "status": "removed"}
        ],
    }
    assert [entry.id for entry in untested(data)] == ["m.py::run"]
    text = render_comment(data)
    assert "Not covered by tests" not in text
    assert "coverage" in text.lower()


def test_opaque_files_do_not_invent_unsupported_language_reason() -> None:
    facts = compute_facts({"files": [{"path": "blob.bin", "kind": "opaque", "language": None}]})
    assert all(entry.reason != "unsupported language" for entry in facts.limits)


def test_analysis_limit_paths_stay_inert_in_comment_markdown(tmp_path: Path) -> None:
    path = "[link](https:evil).go"
    change = custom_map(tmp_path, {}, {path: b"package main\n"})
    text = render_comment(to_jsonable(change))
    assert "analysis is incomplete for 1 file:" in text
    line = next(line for line in text.splitlines() if "evil" in line)
    assert line.startswith("- `[link](https:evil).go`"), line


def test_bracket_filename_gets_literal_line_counts(tmp_path: Path) -> None:
    nl = chr(10)
    change = custom_map(
        tmp_path,
        {},
        {
            "file[1].py": ("first" + nl + "second" + nl + "third" + nl).encode(),
            "file1.py": ("one" + nl).encode(),
        },
    )
    by_path = {f.path: f for f in change.files}
    assert (by_path["file[1].py"].added, by_path["file[1].py"].removed) == (3, 0)
    assert (by_path["file1.py"].added, by_path["file1.py"].removed) == (1, 0)


def test_magic_prefixed_filename_gets_literal_line_counts(tmp_path: Path) -> None:
    nl = chr(10)
    change = custom_map(
        tmp_path,
        {},
        {
            ":(glob)x.py": ("first" + nl + "second" + nl + "third" + nl).encode(),
            "x.py": ("one" + nl + "two" + nl).encode(),
        },
    )
    by_path = {f.path: f for f in change.files}
    assert (by_path[":(glob)x.py"].added, by_path[":(glob)x.py"].removed) == (3, 0)
    assert (by_path["x.py"].added, by_path["x.py"].removed) == (2, 0)


def test_magic_prefixed_filename_without_neighbor_does_not_traceback(tmp_path: Path) -> None:
    nl = chr(10)
    change = custom_map(tmp_path, {}, {":(glob)absent.py": ("one" + nl + "two" + nl).encode()})
    by_path = {f.path: f for f in change.files}
    assert (by_path[":(glob)absent.py"].added, by_path[":(glob)absent.py"].removed) == (2, 0)


def test_tab_filename_keeps_literal_line_counts(tmp_path: Path) -> None:
    nl = chr(10)
    tab = chr(9)
    path = "a" + tab + "b.py"
    change = custom_map(tmp_path, {}, {path: ("one" + nl + "two" + nl + "three" + nl).encode()})
    by_path = {f.path: f for f in change.files}
    assert (by_path[path].added, by_path[path].removed) == (3, 0)


def test_renamed_path_reports_delete_and_add_counts(tmp_path: Path) -> None:
    nl = chr(10)
    change = custom_map(
        tmp_path,
        {"old.py": ("old" + nl).encode()},
        {"new.py": ("old" + nl + "new" + nl).encode()},
    )
    by_path = {f.path: f for f in change.files}
    assert (by_path["old.py"].added, by_path["old.py"].removed) == (0, 1)
    assert (by_path["new.py"].added, by_path["new.py"].removed) == (2, 0)

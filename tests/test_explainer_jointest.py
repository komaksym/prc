"""Join test: the 25 bakeoff fixtures through the ported jointest."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import prc.explainer.jointest as jointest

DATA = Path(__file__).resolve().parent / "data" / "explainer"
SYN_MAP = str(DATA / "jointest" / "synthetic_map.json")
PR12_MAP = str(DATA / "maps" / "pr12.json")

# (fixture, map args, expected exit, code that must appear in output)
CASES = [
    ("pass_real", PR12_MAP, 0, None),
    ("pass_real_cut0", PR12_MAP, 0, None),
    ("pass_synth", SYN_MAP, 0, None),
    ("bad_01_marker_prefix", PR12_MAP, 1, "MARKER"),
    ("bad_02_transformer_stripped", SYN_MAP, 1, "TRANSFORMER"),
    ("bad_03_tab_kept", SYN_MAP, 1, "TAB"),
    ("bad_03_tab_two_spaces", SYN_MAP, 1, "TAB"),
    ("bad_04_trailing_kept", SYN_MAP, 1, "TRAILING_WS"),
    ("bad_05_crlf_kept", SYN_MAP, 1, "CR"),
    ("bad_06_entity_escaped", PR12_MAP, 1, "ENTITY"),
    ("bad_06_entity_synthetic", SYN_MAP, 1, "ENTITY"),
    ("bad_07_midframe_ghost", PR12_MAP, 1, "MIDFRAME"),
    ("bad_09_long_clipped", SYN_MAP, 1, "TRUNCATED"),
    ("bad_10_empty_placeholder", SYN_MAP, 1, "ZEROWIDTH"),
    ("bad_10_empty_vanishes", SYN_MAP, 1, "ROW_COUNT"),
    ("bad_11_nbsp_indent", PR12_MAP, 1, "NBSP"),
    ("bad_11_indent_collapsed", PR12_MAP, 1, "INDENT"),
    ("bad_11_cut_not_spaces", PR12_MAP, 1, "CUT_NOT_SPACES"),
    ("bad_11_cut_inconsistent", PR12_MAP, 1, "CUT_MISMATCH"),
    ("bad_12_row_count", PR12_MAP, 1, "ROW_COUNT"),
    ("bad_12_ref_order", PR12_MAP, 1, "REF_ORDER"),
    ("bad_12_multiline_token", PR12_MAP, 1, "MULTILINE_TOKEN"),
    ("bad_13_gutter_leak", PR12_MAP, 1, "GUTTER"),
    ("bad_14_unicode_minus_marker", PR12_MAP, 1, "MARKER"),
    ("bad_14_nfc_normalized", SYN_MAP, 1, "NFC"),
]


@pytest.mark.parametrize(("name", "map_path", "rc", "code"), CASES)
def test_jointest_fixture(name: str, map_path: str, rc: int, code: str | None) -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        got = jointest.main([str(DATA / "jointest" / f"{name}.json"), "--map", map_path])
    out = buf.getvalue()

    assert got == rc, (name, out)

    if code is not None:
        assert code in out, (name, out)
    else:
        assert "PASS" in out, (name, out)


def test_jointest_requires_map() -> None:
    with pytest.raises(SystemExit):
        jointest.main([str(DATA / "jointest" / "pass_synth.json")])

"""Sample the actual rendered video timeline, including numeric cue positions."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/eval/frames.py"
spec = importlib.util.spec_from_file_location("eval_frames_under_test", SCRIPT)
assert spec and spec.loader
frames = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frames)


def test_rendered_scene_ends_and_cues_use_recorded_times() -> None:
    board = {
        "scenes": [
            {
                "start": 0.0,
                "end": 10.0,
                "say": ["Short sentence."],
                "cues": [{"at": [0, 0.2], "t": 3.0}],
            },
            {
                "start": 10.0,
                "end": 40.0,
                "say": ["Another short sentence."],
                "cues": [{"at": "Another", "t": 24.0}],
            },
        ]
    }
    assert [(item["label"], item["t"]) for item in frames.list_frames(board, 40.0)] == [
        ("scene00_cue", 3.6),
        ("scene00_end", 9.5),
        ("scene01_cue", 24.6),
        ("scene01_end", 39.5),
    ]


def test_untimed_boards_keep_the_estimated_fallback() -> None:
    board = {"scenes": [{"say": ["A short sentence."]}, {"say": ["A short sentence."]}]}
    assert [item["t"] for item in frames.list_frames(board, 20.0)] == [9.5, 19.5]

"""Spoken text: code names in narration become words Kokoro can say."""

from __future__ import annotations

import pytest

from prc.explainer.check import find_phrase, spoken
from prc.explainer.speech import code_tokens, speakable


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("the user gets s2e3.", "the user gets S 2 E 3."),
        ("Up next used to pick s1e1.", "Up next used to pick S 1 E 1."),
        ("It preserves ErrNotExist.", "It preserves error not exist."),
        ("Now it returns ReadComposeError.", "Now it returns read compose error."),
        ("Start at onComplete in note.ts.", "Start at on complete in note dot T S."),
        (
            "Start at select_next_episode in next_episode.py.",
            "Start at select next episode in next episode dot P Y.",
        ),
        ("A WELCOME10 code.", "A WELCOME 10 code."),
        ("It reads parseYAMLFile.", "It reads parse YAML file."),
    ],
)
def test_code_names_become_words(text: str, said: str) -> None:
    """Defect: Kokoro read s2e3 as "ess ee" and ErrNotExist as "earn not exist"."""
    assert speakable(text) == said


@pytest.mark.parametrize(
    "text",
    [
        "Note closes the Command Center on touch.",
        "The A.I. step stays, e.g. on open PRs.",
        "Invalid YAML returns an error, and PRC can quote it.",
        "The 3rd test runs 10 times in 2026.",
        "Season two, episode three.",
    ],
)
def test_plain_prose_is_untouched(text: str) -> None:
    """Defect: a rewrite that mangles ordinary words, acronyms, numbers or a writer's speak text."""
    assert speakable(text) == text


def test_rewrite_is_stable() -> None:
    """Defect: rewriting twice drifts, so explicit speak text and cue phrases stop matching."""
    text = "Start at onComplete in note.ts, then s2e3 and ErrNotExist."
    assert speakable(speakable(text)) == speakable(text)


def test_code_tokens_are_found_in_spoken_order() -> None:
    assert code_tokens("Now `select_next_episode` returns s2e3 from next_episode.py.") == [
        "select_next_episode",
        "s2e3",
        "next_episode.py",
    ]
    assert code_tokens("Note closes the Command Center on touch, with YAML and A.I.") == []


def test_captions_keep_code_and_cues_still_match() -> None:
    """Defect: the rewrite leaks into captions, or a cue phrase naming code stops matching."""
    scene = {"say": ["Now it calls `select_next_episode` for each show."]}
    assert spoken(scene) == ["Now it calls select next episode for each show."]
    assert find_phrase(scene, "calls select_next_episode") == [(0, 7)]


def test_explicit_speak_text_wins() -> None:
    line = {"show": "The user gets s2e3.", "speak": "The user gets season two, episode three."}
    assert spoken({"say": [line]}) == ["The user gets season two, episode three."]

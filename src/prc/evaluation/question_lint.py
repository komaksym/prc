"""Question lint for study v3: the parent review rules as runnable checks.

Each check returns error strings that name its rule slug and question id, so a
future set with these defects fails loudly instead of shipping to the operator.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

OPTION_BALANCE = "option-balance"
PROMPT_LEAK = "prompt-leak"
CROSS_PAIR_LEAK = "cross-pair-leak"
LATER_CHANGE = "later-change"
TITLE_CUE = "title-cue"

RULES = (OPTION_BALANCE, PROMPT_LEAK, CROSS_PAIR_LEAK, LATER_CHANGE, TITLE_CUE)

_BALANCE_TOLERANCE = 0.25
_SHARED_WORD_THRESHOLD = 3

_LATER_RE = re.compile(
    r"later|follow[\s_-]?ups?|subsequent|outside|history|after\s+(this|the)\s+pr|ground\s+truth",
    re.IGNORECASE,
)
_PR_NUMBER_RE = re.compile(r"#\s*(\d+)")
_WORD_RE = re.compile(r"[a-z0-9]{4,}")
_PATH_LIKE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-/]*\.[A-Za-z0-9]{1,4}")
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")

_STOPWORDS = frozenset(
    {
        "with",
        "from",
        "that",
        "this",
        "into",
        "over",
        "after",
        "before",
        "when",
        "what",
        "which",
        "while",
        "where",
        "does",
        "than",
        "then",
        "them",
        "they",
        "their",
        "there",
        "these",
        "those",
        "have",
        "more",
        "most",
        "other",
        "such",
        "only",
        "just",
        "each",
        "every",
        "both",
        "same",
        "much",
        "many",
        "between",
        "through",
        "without",
        "within",
        "upon",
        "using",
        "used",
        "uses",
        "make",
        "takes",
        "keep",
        "keeps",
        "write",
        "writes",
        "read",
        "reads",
        "return",
        "returns",
        "raise",
        "raises",
        "change",
        "changes",
        "check",
        "checks",
        "build",
        "builds",
        "built",
        "still",
        "already",
        "also",
        "very",
        "plus",
        "until",
        "whenever",
        "under",
        "whether",
        "however",
        "whose",
        "never",
        "across",
        "around",
        "because",
        "cannot",
        "onto",
        "along",
        "via",
    }
)


def _qid(question: Mapping[str, Any]) -> str:
    return str(question.get("qid", "?"))


def check_option_balance(question: Mapping[str, Any]) -> list[str]:
    """Options stay within 25 percent of their mean length. Key is never unique longest."""
    qid = _qid(question)
    if str(question.get("kind")) != "multiple_choice":
        return []
    options = [str(option) for option in (question.get("options") or [])]
    if len(options) < 2:
        return []
    lengths = [len(option) for option in options]
    mean = sum(lengths) / len(lengths)
    errors: list[str] = []
    for index, length in enumerate(lengths):
        if mean > 0 and abs(length - mean) / mean > _BALANCE_TOLERANCE:
            errors.append(
                f"{OPTION_BALANCE} {qid}: option {index} has {length} chars, "
                f"outside 25% of the mean {mean:.0f}"
            )
    key = str(question.get("key", ""))
    if key in options:
        longest = max(lengths)
        shortest = min(lengths)
        if len(key) == longest and lengths.count(longest) == 1:
            errors.append(f"{OPTION_BALANCE} {qid}: the key is the unique longest option")
        if len(key) == shortest and lengths.count(shortest) == 1:
            errors.append(f"{OPTION_BALANCE} {qid}: the key is the unique shortest option")
    return errors


def _evidence_tokens(evidence: Any) -> set[str]:
    """File and symbol names cited by the evidence, lowercased for matching."""
    tokens: set[str] = set()
    items: list[Any] = []
    if isinstance(evidence, str):
        try:
            parsed = json.loads(evidence)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            items = parsed
        else:
            for match in _PATH_LIKE_RE.findall(evidence):
                tokens.add(match.lower())
                tokens.add(match.lower().rsplit("/", 1)[-1])
            return tokens
    elif isinstance(evidence, list):
        items = evidence
    for item in items:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path", ""))
        if path:
            tokens.add(path.lower())
            base = path.lower().rsplit("/", 1)[-1]
            tokens.add(base)
            stem = base.rsplit(".", 1)[0] if "." in base else base
            tokens.add(stem)
        for part in _NON_ALNUM_RE.split(str(item.get("symbol", ""))):
            if len(part) >= 3:
                tokens.add(part.lower())
    return tokens


def check_prompt_leak(question: Mapping[str, Any], title: str) -> list[str]:
    """Prompts may name the PR number and title, never evidence file or symbol names."""
    qid = _qid(question)
    prompt = str(question.get("prompt", ""))
    prompt_low = prompt.lower()
    title_low = (title or "").lower()
    title_words = set(re.findall(r"[a-z0-9]+", title_low))
    offenders: list[str] = []
    for token in sorted(_evidence_tokens(question.get("evidence"))):
        if len(token) < 3 or token in {"com", "www"}:
            continue
        if token in title_low:
            continue
        if any(char in token for char in ("_", ".", "/", "-")):
            if len(token) >= 4 and token in prompt_low:
                offenders.append(token)
        elif (
            len(token) >= 5
            and token not in title_words
            and re.search(r"\b" + re.escape(token) + r"\b", prompt, re.IGNORECASE)
        ):
            offenders.append(token)
    if offenders:
        return [
            f"{PROMPT_LEAK} {qid}: prompt names evidence tokens beyond the title: "
            + ", ".join(offenders)
        ]
    return []


def _stem(word: str) -> str:
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 5 and word.endswith("ers"):
        return word[:-3]
    if len(word) > 5 and word.endswith("er"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _content_sequence(text: str) -> list[str]:
    return [_stem(word) for word in _WORD_RE.findall(text.lower()) if word not in _STOPWORDS]


def _bigrams(sequence: list[str]) -> set[tuple[str, str]]:
    return set(zip(sequence, sequence[1:], strict=False))


def check_title_cue(question: Mapping[str, Any], title: str) -> list[str]:
    """The key may not be the one option that echoes the most PR title words.

    When it is, a reader picks the key from the title alone. This catches the
    lexical cue only; a key that paraphrases the title still needs review.
    """
    qid = _qid(question)
    if str(question.get("kind")) != "multiple_choice":
        return []
    options = [str(option) for option in (question.get("options") or [])]
    key = str(question.get("key", ""))
    if key not in options or len(options) < 2:
        return []
    title_words = set(_content_sequence(title))
    key_shared = sorted(set(_content_sequence(key)) & title_words)
    others = [option for option in options if option != key]
    best_other = max(len(set(_content_sequence(option)) & title_words) for option in others)
    if key_shared and len(key_shared) > best_other:
        return [
            f"{TITLE_CUE} {qid}: only the key shares {len(key_shared)} title words "
            f"({', '.join(key_shared)}); the best other option shares {best_other}"
        ]
    return []


def check_cross_pair_leak(
    qid: str,
    options: Sequence[str],
    own_text: str,
    others: Mapping[str, str],
) -> list[str]:
    """No option may echo another reading. Distinctive shared phrases fail the set."""
    own_seq = _content_sequence(own_text)
    own_bigrams = _bigrams(own_seq)
    own_words = set(own_seq)
    errors: list[str] = []
    for index, option in enumerate(options):
        opt_seq = _content_sequence(str(option))
        opt_bigrams = _bigrams(opt_seq)
        opt_words = set(opt_seq)
        for sid, text in others.items():
            other_seq = _content_sequence(str(text))
            other_bigrams = _bigrams(other_seq)
            shared_phrases = sorted(
                " ".join(pair) for pair in (opt_bigrams & other_bigrams - own_bigrams)
            )
            if shared_phrases:
                errors.append(
                    f"{CROSS_PAIR_LEAK} {qid}: option {index} shares "
                    f"phrase '{shared_phrases[0]}' with reading {sid}"
                )
                continue
            shared_words = sorted((opt_words & set(other_seq)) - own_words)
            if len(shared_words) >= _SHARED_WORD_THRESHOLD:
                errors.append(
                    f"{CROSS_PAIR_LEAK} {qid}: option {index} shares "
                    f"words {shared_words} with reading {sid}"
                )
    return errors


def check_later_change(question: Mapping[str, Any], own_number: str | None = None) -> list[str]:
    """Questions answer from the PR itself. Later changes stay out of the prompt."""
    qid = _qid(question)
    prompt = str(question.get("prompt", ""))
    if _LATER_RE.search(prompt):
        return [f"{LATER_CHANGE} {qid}: prompt asks about a later change"]
    numbers = set(_PR_NUMBER_RE.findall(prompt))
    if own_number is not None:
        foreign = sorted(number for number in numbers if number != str(own_number))
        if foreign:
            return [f"{LATER_CHANGE} {qid}: prompt names other PRs {foreign}"]
    elif len(numbers) >= 2:
        return [f"{LATER_CHANGE} {qid}: prompt names several PRs {sorted(numbers)}"]
    return []


def _own_number(pr_identity: str) -> str | None:
    if "#" not in pr_identity:
        return None
    number = pr_identity.rsplit("#", 1)[-1].strip()
    return number if number.isdigit() else None


def lint_study(
    questions_by_snapshot: Mapping[str, Sequence[Mapping[str, Any]]],
    meta_by_snapshot: Mapping[str, Mapping[str, str]],
) -> list[str]:
    """Run every rule over a full question set. Errors name the rule and qid."""
    own_text = {
        sid: str(meta_by_snapshot.get(sid, {}).get("title", ""))
        + " "
        + " ".join(str(question.get("key", "")) for question in questions_by_snapshot.get(sid, []))
        for sid in questions_by_snapshot
    }
    errors: list[str] = []
    for sid, questions in questions_by_snapshot.items():
        meta = meta_by_snapshot.get(sid, {})
        title = str(meta.get("title", ""))
        number = _own_number(str(meta.get("pr_identity", "")))
        others = {other: own_text[other] for other in own_text if other != sid}
        for question in questions:
            qid = _qid(question)
            errors.extend(check_option_balance(question))
            errors.extend(check_prompt_leak(question, title))
            errors.extend(check_later_change(question, own_number=number))
            if str(question.get("kind")) == "multiple_choice":
                options = [str(option) for option in (question.get("options") or [])]
                errors.extend(check_cross_pair_leak(qid, options, own_text[sid], others))
                errors.extend(check_title_cue(question, title))
    return errors

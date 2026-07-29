"""Cryptogram (monoalphabetic substitution) validation.

Uniqueness for a cryptogram is only meaningful relative to a lexicon: the
puzzle is proper when exactly one sequence of dictionary words is
consistent with a single substitution.  Solutions are counted by
backtracking over the ciphertext words, most-constrained first, extending
a partial symbol-to-letter mapping that must stay injective.

Spec format::

    {
      "ciphertext": "Q LIQKH DOFR ITQKL ZIT LOSTFET WTZVTTF LOUFQSL",
      "wordlist": ["A", "SHARP", ...],        # or a file path string
      "no_self_map": false,                    # forbid symbol == letter
      "given": {"Z": "T", "I": "H"}            # pre-cracked symbols
    }

Cipher symbols may be any characters (Greek glyphs, punctuation-free);
plaintext is A-Z.  Distinct solutions are distinct plaintexts.
"""

from dataclasses import dataclass, field
from typing import Any

from .core import Verdict, load_wordlist
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class Cryptogram:
    words: tuple[str, ...]
    wordlist: frozenset[str]
    no_self_map: bool = False
    given: dict[str, str] = field(default_factory=dict)


def _normalise(text: str) -> str:
    """Uppercase ASCII letters only.

    Non-ASCII cipher glyphs are kept verbatim: unicode case-mapping can
    collapse distinct glyphs (e.g. both π and ϖ uppercase to Π), which
    would silently corrupt the cipher.
    """
    return "".join(ch.upper() if "a" <= ch <= "z" else ch for ch in text)


def parse(spec: dict[str, Any]) -> Cryptogram:
    ciphertext = get_field(spec, "ciphertext", str)
    return Cryptogram(
        words=tuple(_normalise(ciphertext).split()),
        wordlist=load_wordlist(spec.get("wordlist", [])),
        no_self_map=get_field(spec, "no_self_map", bool, False, required=False),
        given={
            _normalise(str(k)): str(v).upper()
            for k, v in get_field(spec, "given", dict, {}, required=False).items()
        },
    )


def check(puzzle: Cryptogram) -> list[str]:
    issues = []
    if not puzzle.words:
        issues.append("ciphertext is empty")
    if len(set(puzzle.given.values())) != len(puzzle.given):
        issues.append("given mappings assign one letter to two symbols")
    if puzzle.no_self_map and any(s == v for s, v in puzzle.given.items()):
        issues.append("a given mapping violates no_self_map")
    return issues


def _consistent(word: str, candidate: str, mapping: dict[str, str]) -> bool:
    """Can ``candidate`` decode ``word`` given the partial ``mapping``?"""
    used = set(mapping.values())
    trial: dict[str, str] = {}
    for symbol, letter in zip(word, candidate, strict=True):
        expected = mapping.get(symbol, trial.get(symbol))
        if expected is not None:
            if expected != letter:
                return False
            continue
        if letter in used or letter in trial.values():
            return False  # substitution must stay injective
        trial[symbol] = letter
    return True


def _search(
    puzzle: Cryptogram,
    order: list[str],
    candidates: dict[str, list[str]],
    mapping: dict[str, str],
    limit: int,
    found: list[str],
) -> None:
    if len(found) >= limit:
        return
    if not order:
        decoded = " ".join(
            "".join(mapping[s] for s in word) for word in puzzle.words
        )
        if decoded not in found:
            found.append(decoded)
        return
    # Most-constrained word first, judged against the current mapping.
    word = min(
        order,
        key=lambda w: sum(_consistent(w, c, mapping) for c in candidates[w]),
    )
    rest = [w for w in order if w != word]
    for candidate in candidates[word]:
        if not _consistent(word, candidate, mapping):
            continue
        added = {
            s: letter
            for s, letter in zip(word, candidate, strict=True)
            if s not in mapping
        }
        mapping.update(added)
        _search(puzzle, rest, candidates, mapping, limit, found)
        for symbol in added:
            del mapping[symbol]
        if len(found) >= limit:
            return


def validate(puzzle: Cryptogram, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("cryptogram", issues)

    by_length: dict[int, list[str]] = {}
    for entry in puzzle.wordlist:
        by_length.setdefault(len(entry), []).append(entry)

    def matches(word: str) -> list[str]:
        pattern = _pattern(word)
        pool = by_length.get(len(word), [])
        candidates = [c for c in sorted(pool) if _pattern(c) == pattern]
        if puzzle.no_self_map:
            candidates = [
                c
                for c in candidates
                if all(s != letter for s, letter in zip(word, c, strict=True))
            ]
        return candidates

    unique_words = sorted(set(puzzle.words))
    candidates = {word: matches(word) for word in unique_words}
    if empty := [w for w in unique_words if not candidates[w]]:
        return Verdict(
            puzzle_type="cryptogram",
            well_formed=True,
            issues=[f"no dictionary word matches the pattern of {w!r}" for w in empty],
            solution_count=0,
        )

    found: list[str] = []
    _search(puzzle, unique_words, candidates, dict(puzzle.given), limit, found)
    return Verdict(
        puzzle_type="cryptogram",
        well_formed=True,
        solution_count=len(found),
        solutions=found,
    )


def _pattern(word: str) -> tuple[int, ...]:
    """Repeat structure of a word: ABBA and NOON share (0, 1, 1, 0)."""
    seen: dict[str, int] = {}
    return tuple(seen.setdefault(ch, len(seen)) for ch in word)

"""Word-ladder validation.

A ladder is a chain of equal-length dictionary words, each differing from
the previous in exactly one position.  Given the endpoints and length, the
puzzle is proper when exactly one ladder connects them within the
wordlist; when explicit ``steps`` are supplied they are checked and must
be that unique ladder.

Spec format::

    {
      "steps": ["MAZE", "MACE", "RACE", ...],  # optional full chain
      "start": "MAZE",                          # required if no steps
      "end": "HERE",
      "length": 9,                              # total words in the chain
      "wordlist": ["MAZE", "MACE", ...]         # or a file path string
    }
"""

from dataclasses import dataclass
from typing import Any

from .core import Verdict, load_wordlist
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class WordLadder:
    start: str
    end: str
    length: int
    wordlist: frozenset[str]
    steps: tuple[str, ...] = ()


def parse(spec: dict[str, Any]) -> WordLadder:
    steps = tuple(
        str(w).upper() for w in get_field(spec, "steps", list, [], required=False)
    )
    if steps:
        start, end, length = steps[0], steps[-1], len(steps)
    else:
        start = get_field(spec, "start", str).upper()
        end = get_field(spec, "end", str).upper()
        length = get_field(spec, "length", int)
    return WordLadder(
        start=start,
        end=end,
        length=length,
        wordlist=load_wordlist(spec.get("wordlist", [])),
        steps=steps,
    )


def differ_by_one(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b, strict=True)) == 1


def check(puzzle: WordLadder) -> list[str]:
    issues = []
    if len(puzzle.start) != len(puzzle.end):
        issues.append("start and end words must have the same length")
    if puzzle.length < 2:
        issues.append("a ladder needs at least two steps")
    for word in (puzzle.start, puzzle.end):
        if word not in puzzle.wordlist:
            issues.append(f"{word!r} is not in the wordlist")
    if puzzle.steps:
        if len(puzzle.steps) != len(set(puzzle.steps)):
            issues.append("steps must not repeat a word")
        for word in puzzle.steps:
            if word not in puzzle.wordlist:
                issues.append(f"step {word!r} is not in the wordlist")
        for a, b in zip(puzzle.steps, puzzle.steps[1:], strict=False):
            if not differ_by_one(a, b):
                issues.append(
                    f"{a!r} -> {b!r} does not change exactly one letter"
                )
    return issues


def _ladders(puzzle: WordLadder, limit: int) -> list[list[str]]:
    """All simple ladders of the required length, up to ``limit``."""
    pool = [w for w in puzzle.wordlist if len(w) == len(puzzle.start)]
    neighbours: dict[str, list[str]] = {w: [] for w in pool}
    for i, a in enumerate(pool):
        for b in pool[i + 1 :]:
            if differ_by_one(a, b):
                neighbours[a].append(b)
                neighbours[b].append(a)

    found: list[list[str]] = []
    path = [puzzle.start]

    def extend() -> None:
        if len(found) >= limit:
            return
        if len(path) == puzzle.length:
            if path[-1] == puzzle.end:
                found.append(list(path))
            return
        for nxt in sorted(neighbours[path[-1]]):
            if nxt in path:
                continue
            path.append(nxt)
            extend()
            path.pop()
            if len(found) >= limit:
                return

    extend()
    return found


def validate(puzzle: WordLadder, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("wordladder", issues)

    solutions = _ladders(puzzle, limit)
    verdict_issues = []
    exhaustive = len(solutions) < limit
    if puzzle.steps and exhaustive and list(puzzle.steps) not in solutions:
        verdict_issues.append(
            "the supplied steps are not among the ladders found"
        )
    return Verdict(
        puzzle_type="wordladder",
        well_formed=True,
        issues=verdict_issues,
        solution_count=len(solutions),
        solutions=solutions,
    )

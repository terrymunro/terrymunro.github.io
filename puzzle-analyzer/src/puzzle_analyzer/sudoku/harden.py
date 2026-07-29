"""Suggest changes that make a puzzle harder without changing its solution.

The only change that provably preserves the solution is *removing givens*:
the solution grid stays identical as long as the reduced puzzle still has
exactly one solution (verified with OR-Tools).  Each candidate removal is
additionally required to stay solvable by the human technique repertoire,
so hardened puzzles never need guessing.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .analyze import Analysis, analyze
from .difficulty import Rating, rate
from .grid import cell_name
from .solver import solve_logically
from .uniqueness import is_unique


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Remove the given at ``cell`` (its value is ``digit``)."""

    cell: int
    digit: int
    rating: Rating
    new_puzzle: list[int]

    def describe(self) -> str:
        return (
            f"remove the {self.digit} at {cell_name(self.cell)} -> "
            f"{self.rating.grade} (hardest: {self.rating.hardest_technique}, "
            f"score {self.rating.score})"
        )


@dataclass(frozen=True, slots=True)
class HardenReport:
    base: Analysis
    suggestions: list[Suggestion]
    #: Givens whose removal makes the solution non-unique.
    breaks_uniqueness: list[int]
    #: Givens whose removal keeps uniqueness but requires guessing.
    breaks_solvability: list[int]


def suggest_removals(values: Sequence[int]) -> HardenReport:
    """Evaluate every single-given removal and rank the ones that help.

    Suggestions are removals that keep the puzzle unique AND logically
    solvable, sorted hardest-first.  Removals that merely keep the current
    difficulty are included too (they still make the puzzle sparser), but
    ones that would lower the score are dropped.
    """
    base = analyze(values)
    suggestions: list[Suggestion] = []
    breaks_uniqueness: list[int] = []
    breaks_solvability: list[int] = []

    if not base.valid or not base.solvable_without_guessing:
        return HardenReport(base, [], [], [])

    for cell, digit in enumerate(values):
        if not digit:
            continue
        trial = list(values)
        trial[cell] = 0
        if not is_unique(trial):
            breaks_uniqueness.append(cell)
            continue
        result = solve_logically(trial)
        if not result.solved:
            breaks_solvability.append(cell)
            continue
        rating = rate(result)
        if rating.score >= base.rating.score:
            suggestions.append(Suggestion(cell, digit, rating, trial))

    suggestions.sort(key=lambda s: (-s.rating.score, s.cell))
    return HardenReport(base, suggestions, breaks_uniqueness, breaks_solvability)


def greedy_harden(
    values: Sequence[int], max_removals: int | None = None
) -> list[Suggestion]:
    """Repeatedly apply the best strictly-improving removal.

    Returns the chain of applied suggestions; the last one's ``new_puzzle``
    is the hardest variant found.  Greedy, so not guaranteed optimal, but
    each intermediate puzzle is verified unique and guess-free.
    """
    current = list(values)
    applied: list[Suggestion] = []
    while max_removals is None or len(applied) < max_removals:
        report = suggest_removals(current)
        improving = [
            s
            for s in report.suggestions
            if s.rating.score > report.base.rating.score
        ]
        if not improving:
            break
        best = improving[0]
        applied.append(best)
        current = best.new_puzzle
    return applied

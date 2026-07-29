"""A generic hardening engine.

A *reduction* is a single edit that plausibly makes a puzzle harder
without changing what the solution is — deleting a clue, hiding a number,
merging two cages.  Each puzzle module that supports hardening exposes
``reductions(puzzle)`` yielding candidate edits; this engine does the
bookkeeping that must never be skipped:

* the reduced puzzle must still have **exactly one solution** (re-proved
  via the module's validator), and that solution must be **the same**;
* the reduced puzzle must still be **solvable without search** (re-graded
  via the module's grader), so hardening never crosses into guessing;
* candidates are ranked by the grading score.

The engine is deliberately decoupled: it receives the module's
``validate``/``grade``/``reductions`` callables instead of importing any
puzzle module, so it works for every current and future type.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .grading import Rating
from .verdict import Verdict


@dataclass(frozen=True, slots=True)
class Reduction:
    """One candidate edit produced by a puzzle module."""

    description: str
    puzzle: Any


@dataclass(frozen=True, slots=True)
class Suggestion:
    description: str
    rating: Rating
    puzzle: Any

    def describe(self) -> str:
        return f"{self.description} -> {self.rating.grade} (score {self.rating.score})"


@dataclass(frozen=True, slots=True)
class HardenReport:
    base_verdict: Verdict
    base_rating: Rating | None
    suggestions: list[Suggestion]
    #: Reductions rejected because uniqueness or the solution would break.
    breaks_uniqueness: list[str]
    #: Reductions rejected because the puzzle would need guessing.
    breaks_solvability: list[str]

    @property
    def viable(self) -> bool:
        return self.base_verdict.unique and self.base_rating is not None


type Validate = Callable[..., Verdict]
type Grade = Callable[[Any], Rating]
type Reductions = Callable[[Any], Iterable[Reduction]]
type SolutionKey = Callable[[Any], Any]


def suggest(
    puzzle: Any,
    *,
    validate: Validate,
    grade: Grade,
    reductions: Reductions,
    solution_key: SolutionKey = lambda solution: solution,
) -> HardenReport:
    """Evaluate every single reduction and rank the ones that hold up."""
    base_verdict = validate(puzzle)
    if not base_verdict.unique:
        return HardenReport(base_verdict, None, [], [], [])
    base_rating = grade(puzzle)
    if not base_rating.solved_without_search:
        return HardenReport(base_verdict, base_rating, [], [], [])

    base_solution = solution_key(base_verdict.solution)
    suggestions: list[Suggestion] = []
    breaks_uniqueness: list[str] = []
    breaks_solvability: list[str] = []

    for reduction in reductions(puzzle):
        verdict = validate(reduction.puzzle)
        if not verdict.unique or solution_key(verdict.solution) != base_solution:
            breaks_uniqueness.append(reduction.description)
            continue
        rating = grade(reduction.puzzle)
        if not rating.solved_without_search:
            breaks_solvability.append(reduction.description)
            continue
        if rating.score >= base_rating.score:
            suggestions.append(
                Suggestion(reduction.description, rating, reduction.puzzle)
            )

    suggestions.sort(key=lambda s: (-s.rating.score, s.description))
    return HardenReport(
        base_verdict, base_rating, suggestions, breaks_uniqueness, breaks_solvability
    )


def greedy(
    puzzle: Any,
    *,
    validate: Validate,
    grade: Grade,
    reductions: Reductions,
    solution_key: SolutionKey = lambda solution: solution,
    max_steps: int | None = None,
) -> list[Suggestion]:
    """Repeatedly apply the best strictly-improving reduction.

    Returns the chain of applied suggestions; the last one's ``puzzle`` is
    the hardest variant found.  Greedy, so not guaranteed optimal, but
    every intermediate stays unique, solution-preserving and guess-free.
    """
    current = puzzle
    applied: list[Suggestion] = []
    while max_steps is None or len(applied) < max_steps:
        report = suggest(
            current,
            validate=validate,
            grade=grade,
            reductions=reductions,
            solution_key=solution_key,
        )
        if report.base_rating is None:
            break
        improving = [
            s
            for s in report.suggestions
            if s.rating.score > report.base_rating.score
        ]
        if not improving:
            break
        best = improving[0]
        applied.append(best)
        current = best.puzzle
    return applied

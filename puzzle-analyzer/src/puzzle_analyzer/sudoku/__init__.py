"""Sudoku: uniqueness validation, annotated logical solving and hardening.

The richest module in the analyzer: besides the uniqueness check every
puzzle type gets, sudoku has a human-technique solver that annotates every
step, a difficulty grader, and a hardener that suggests given-removals.
"""

from typing import Any

from ..core import Rating as CoreRating
from ..core import Reduction, Verdict
from .analyze import Analysis, analyze
from .board import Board
from .difficulty import Rating, rate
from .grid import cell_name, format_grid, parse_puzzle, to_line
from .harden import HardenReport, Suggestion, greedy_harden, suggest_removals
from .solver import SolveResult, solve_logically
from .techniques import TECHNIQUES, Step
from .uniqueness import count_solutions, is_unique

__all__ = [
    "TECHNIQUES",
    "Analysis",
    "Board",
    "HardenReport",
    "Rating",
    "SolveResult",
    "Step",
    "Suggestion",
    "analyze",
    "count_solutions",
    "format_grid",
    "grade",
    "greedy_harden",
    "is_unique",
    "parse",
    "parse_puzzle",
    "rate",
    "reductions",
    "solve_logically",
    "suggest_removals",
    "to_line",
    "validate",
]


def parse(spec: str | dict[str, Any]) -> list[int]:
    """Registry entry point: accept a raw 81-char string or ``{"givens": ...}``."""
    if isinstance(spec, dict):
        spec = spec["givens"]
    return parse_puzzle(spec)


def validate(values: list[int], *, limit: int = 2) -> Verdict:
    """Registry entry point: uniqueness verdict plus sudoku-specific extras."""
    analysis = analyze(values)
    details: dict[str, Any] = {}
    if analysis.rating is not None and analysis.solve is not None:
        details = {
            "solvableWithoutGuessing": analysis.solvable_without_guessing,
            "grade": analysis.rating.grade,
            "hardestTechnique": analysis.rating.hardest_technique,
            "score": analysis.rating.score,
            "techniqueCounts": analysis.solve.technique_counts,
        }
    return Verdict(
        puzzle_type="sudoku",
        well_formed=not analysis.conflicts,
        issues=analysis.conflicts,
        solution_count=analysis.solution_count,
        solutions=[to_line(analysis.solution)] if analysis.solution else [],
        details=details,
    )


def grade(values: list[int]) -> CoreRating:
    """Registry entry point: technique-based grading on the shared scale.

    Sudoku keeps its bespoke human-technique solver (richer than the
    generic propagation engine) but reports through the same
    :class:`~puzzle_analyzer.core.Rating` shape as every other type.
    """
    analysis = analyze(values)
    if analysis.rating is None or analysis.solve is None:
        return CoreRating(
            grade="Invalid",
            score=0.0,
            solved_without_search=False,
            detail={"conflicts": analysis.conflicts},
        )
    return CoreRating(
        grade=analysis.rating.grade,
        score=analysis.rating.score,
        solved_without_search=analysis.solvable_without_guessing,
        steps=[
            f"[{step.technique}] {step.description}"
            for step in analysis.solve.steps
        ],
        detail={
            "hardestTechnique": analysis.rating.hardest_technique,
            "techniqueCounts": analysis.solve.technique_counts,
        },
    )


def reductions(values: list[int]):
    """Registry entry point: hardening moves are single given-removals."""
    for cell, digit in enumerate(values):
        if digit:
            reduced = list(values)
            reduced[cell] = 0
            yield Reduction(
                f"remove the {digit} at {cell_name(cell)}", reduced
            )

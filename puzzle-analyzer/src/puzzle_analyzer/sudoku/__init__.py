"""Sudoku: uniqueness validation, annotated logical solving and hardening.

The richest module in the analyzer: besides the uniqueness check every
puzzle type gets, sudoku has a human-technique solver that annotates every
step, a difficulty grader, and a hardener that suggests given-removals.
"""

from typing import Any

from ..core import Verdict
from .analyze import Analysis, analyze
from .board import Board
from .difficulty import Rating, rate
from .grid import format_grid, parse_puzzle, to_line
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
    "greedy_harden",
    "is_unique",
    "parse",
    "parse_puzzle",
    "rate",
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

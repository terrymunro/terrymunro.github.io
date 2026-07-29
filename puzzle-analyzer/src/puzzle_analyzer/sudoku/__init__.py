"""Sudoku: uniqueness validation, annotated logical solving and hardening.

The richest module in the analyzer: besides the uniqueness check every
puzzle type gets, sudoku has a human-technique solver that annotates every
step, a difficulty grader, and a hardener that suggests given-removals.
"""

from typing import Any

from ..core import Rating as CoreRating
from ..core import Reduction, Verdict
from . import fpuzzles
from .analyze import Analysis, analyze
from .board import Board
from .difficulty import Rating, rate
from .grid import cell_name, format_grid, parse_puzzle, to_line
from .harden import HardenReport, Suggestion, greedy_harden, suggest_removals
from .model import Cage, SudokuPuzzle, Variants, parse_spec
from .solver import SolveResult, as_puzzle, solve_logically
from .techniques import TECHNIQUES, Step
from .uniqueness import count_solutions, is_unique

__all__ = [
    "TECHNIQUES",
    "Analysis",
    "Board",
    "Cage",
    "HardenReport",
    "Rating",
    "SolveResult",
    "Step",
    "SudokuPuzzle",
    "Suggestion",
    "Variants",
    "analyze",
    "as_puzzle",
    "count_solutions",
    "format_grid",
    "fpuzzles",
    "grade",
    "greedy_harden",
    "is_unique",
    "parse",
    "parse_puzzle",
    "parse_spec",
    "rate",
    "reductions",
    "solve_logically",
    "suggest_removals",
    "to_line",
    "validate",
]


def parse(spec: str | dict[str, Any] | SudokuPuzzle) -> SudokuPuzzle:
    """Registry entry point.

    Accepts a classic 81-char string, a JSON spec dict (see
    :mod:`~puzzle_analyzer.sudoku.model` for variant fields), an f-puzzles
    URL / ``{"fpuzzles": url}``, or an already-parsed puzzle.
    """
    if isinstance(spec, SudokuPuzzle):
        return spec
    if isinstance(spec, dict):
        if "fpuzzles" in spec:
            return parse_spec(fpuzzles.decode(spec["fpuzzles"]))
        return parse_spec(spec)
    text = spec.strip()
    if "?load=" in text or "f-puzzles.com" in text:
        return parse_spec(fpuzzles.decode(text))
    return SudokuPuzzle(values=tuple(parse_puzzle(text)))


def validate(values: "list[int] | SudokuPuzzle", *, limit: int = 2) -> Verdict:
    """Registry entry point: uniqueness verdict plus sudoku-specific extras."""
    puzzle = as_puzzle(values)
    analysis = analyze(puzzle)
    details: dict[str, Any] = {}
    if variants := puzzle.variants.describe():
        details["variants"] = variants
    if analysis.rating is not None and analysis.solve is not None:
        details |= {
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


def grade(values: "list[int] | SudokuPuzzle") -> CoreRating:
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


def reductions(values: "list[int] | SudokuPuzzle"):
    """Registry entry point: hardening moves are single given-removals."""
    from dataclasses import replace

    puzzle = as_puzzle(values)
    for cell, digit in enumerate(puzzle.values):
        if digit:
            grid = list(puzzle.values)
            grid[cell] = 0
            yield Reduction(
                f"remove the {digit} at {cell_name(cell)}",
                replace(puzzle, values=tuple(grid)),
            )

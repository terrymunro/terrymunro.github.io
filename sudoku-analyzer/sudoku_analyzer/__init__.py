"""Sudoku validation, grading, annotation and hardening.

Public API:

* :func:`analyze` — full report: well-formedness, uniqueness (OR-Tools),
  guess-free solvability, difficulty grade.
* :func:`solve_logically` — annotated step-by-step logical solve.
* :func:`count_solutions` / :func:`is_unique` — CP-SAT solution counting.
* :func:`suggest_removals` / :func:`greedy_harden` — make a puzzle harder
  while preserving its unique solution and guess-free solvability.
"""

from .analyze import Analysis, analyze
from .difficulty import Rating, rate
from .grid import format_grid, parse_puzzle, to_line
from .harden import HardenReport, Suggestion, greedy_harden, suggest_removals
from .solver import SolveResult, solve_logically
from .uniqueness import count_solutions, is_unique

__all__ = [
    "Analysis",
    "analyze",
    "Rating",
    "rate",
    "format_grid",
    "parse_puzzle",
    "to_line",
    "HardenReport",
    "Suggestion",
    "greedy_harden",
    "suggest_removals",
    "SolveResult",
    "solve_logically",
    "count_solutions",
    "is_unique",
]

__version__ = "1.0.0"

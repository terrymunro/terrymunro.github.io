"""High-level analysis combining validity, uniqueness and gradability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .difficulty import Rating, rate
from .grid import find_given_conflicts
from .solver import SolveResult, solve_logically
from .uniqueness import count_solutions


@dataclass
class Analysis:
    values: List[int]
    #: Duplicate-given conflicts; non-empty means the puzzle is malformed.
    conflicts: List[str]
    #: 0, 1 or 2 (2 means "two or more").
    solution_count: int
    solution: Optional[List[int]]
    solve: Optional[SolveResult]
    rating: Optional[Rating]

    @property
    def valid(self) -> bool:
        """Well-formed with exactly one solution."""
        return not self.conflicts and self.solution_count == 1

    @property
    def solvable_without_guessing(self) -> bool:
        return bool(self.solve and self.solve.solved)


def analyze(values: Sequence[int]) -> Analysis:
    values = list(values)
    conflicts = find_given_conflicts(values)
    if conflicts:
        return Analysis(values, conflicts, 0, None, None, None)

    solutions = count_solutions(values, limit=2)
    if len(solutions) != 1:
        return Analysis(values, [], len(solutions), None, None, None)

    result = solve_logically(values)
    return Analysis(values, [], 1, solutions[0], result, rate(result))

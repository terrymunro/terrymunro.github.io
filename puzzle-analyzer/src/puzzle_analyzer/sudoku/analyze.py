"""High-level analysis combining validity, uniqueness and gradability."""

from collections.abc import Sequence
from dataclasses import dataclass

from .difficulty import Rating, rate
from .model import SudokuPuzzle, find_conflicts
from .solver import SolveResult, as_puzzle, solve_logically
from .uniqueness import count_solutions


@dataclass(slots=True)
class Analysis:
    values: list[int]
    #: Duplicate-given conflicts; non-empty means the puzzle is malformed.
    conflicts: list[str]
    #: 0, 1 or 2 (2 means "two or more").
    solution_count: int
    solution: list[int] | None
    solve: SolveResult | None
    rating: Rating | None

    @property
    def valid(self) -> bool:
        """Well-formed with exactly one solution."""
        return not self.conflicts and self.solution_count == 1

    @property
    def solvable_without_guessing(self) -> bool:
        return bool(self.solve and self.solve.solved)


def analyze(values: "Sequence[int] | SudokuPuzzle") -> Analysis:
    puzzle = as_puzzle(values)
    grid = list(puzzle.values)
    conflicts = find_conflicts(puzzle)
    if conflicts:
        return Analysis(grid, conflicts, 0, None, None, None)

    solutions = count_solutions(puzzle, limit=2)
    if len(solutions) != 1:
        return Analysis(grid, [], len(solutions), None, None, None)

    result = solve_logically(puzzle)
    return Analysis(grid, [], 1, solutions[0], result, rate(result))

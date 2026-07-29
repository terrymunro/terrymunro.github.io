"""Solution counting with Google OR-Tools CP-SAT.

CP-SAT proves whether a puzzle has zero, exactly one, or multiple solutions
by enumerating solutions with a hard stop after the requested limit.
"""

from __future__ import annotations

from typing import List, Sequence

from ortools.sat.python import cp_model

from .grid import BOXES


class _SolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, cells, limit: int):
        super().__init__()
        self._cells = cells
        self._limit = limit
        self.solutions: List[List[int]] = []

    def on_solution_callback(self) -> None:
        self.solutions.append(
            [self.value(self._cells[r][c]) for r in range(9) for c in range(9)]
        )
        if len(self.solutions) >= self._limit:
            self.stop_search()


def count_solutions(values: Sequence[int], limit: int = 2) -> List[List[int]]:
    """Return up to ``limit`` distinct solutions of the puzzle.

    ``len(result) == 0``: unsolvable; ``== 1``: unique; ``>= 2``: multiple
    solutions (only ``limit`` are enumerated, there may be more).
    """
    model = cp_model.CpModel()
    cells = [
        [model.new_int_var(1, 9, f"c{r}{c}") for c in range(9)]
        for r in range(9)
    ]

    for r in range(9):
        model.add_all_different(cells[r])
    for c in range(9):
        model.add_all_different([cells[r][c] for r in range(9)])
    for box in BOXES:
        model.add_all_different([cells[i // 9][i % 9] for i in box])

    for i, v in enumerate(values):
        if v:
            model.add(cells[i // 9][i % 9] == v)

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    collector = _SolutionCollector(cells, limit)
    solver.solve(model, collector)
    return collector.solutions


def is_unique(values: Sequence[int]) -> bool:
    return len(count_solutions(values, limit=2)) == 1

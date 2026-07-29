"""Shared CP-SAT plumbing: model building and exact solution enumeration.

Every constraint-based puzzle module builds its model through
:class:`CpModelBuilder` and counts solutions with
:func:`enumerate_solutions`; uniqueness is therefore always a proof
(enumeration with a hard stop), never a heuristic.
"""

from collections.abc import Callable, Sequence
from typing import Self

from ortools.sat.python import cp_model


class CpModelBuilder:
    """A thin convenience wrapper over ``cp_model.CpModel``.

    Exposes the raw model for arbitrary constraints while providing the
    grid-puzzle staples (integer grids, Latin-square rows/columns) that
    several puzzle types share.
    """

    def __init__(self) -> None:
        self.model = cp_model.CpModel()

    def int_grid(
        self, rows: int, cols: int, lo: int, hi: int, name: str = "cell"
    ) -> list[list[cp_model.IntVar]]:
        return [
            [
                self.model.new_int_var(lo, hi, f"{name}_{r}_{c}")
                for c in range(cols)
            ]
            for r in range(rows)
        ]

    def bool_grid(
        self, rows: int, cols: int, name: str = "cell"
    ) -> list[list[cp_model.IntVar]]:
        return [
            [self.model.new_bool_var(f"{name}_{r}_{c}") for c in range(cols)]
            for r in range(rows)
        ]

    def latin_square(
        self, grid: Sequence[Sequence[cp_model.IntVar]]
    ) -> Self:
        """Constrain an n×n grid so each row and column is a permutation."""
        n = len(grid)
        for r in range(n):
            self.model.add_all_different(grid[r])
        for c in range(n):
            self.model.add_all_different([grid[r][c] for r in range(n)])
        return self

    def fix_givens(
        self,
        grid: Sequence[Sequence[cp_model.IntVar]],
        givens: Sequence[Sequence[int]],
        blank: int = 0,
    ) -> Self:
        for r, row in enumerate(givens):
            for c, v in enumerate(row):
                if v != blank:
                    self.model.add(grid[r][c] == v)
        return self


class _Collector[T](cp_model.CpSolverSolutionCallback):
    def __init__(
        self,
        variables: Sequence[cp_model.IntVar],
        limit: int,
        decode: Callable[[list[int]], T],
        accept: Callable[[list[int]], bool] | None,
    ) -> None:
        super().__init__()
        self._variables = variables
        self._limit = limit
        self._decode = decode
        self._accept = accept
        self._seen: set[tuple[int, ...]] = set()
        self.solutions: list[T] = []

    def on_solution_callback(self) -> None:
        values = [self.value(v) for v in self._variables]
        key = tuple(values)
        if key in self._seen:
            return  # same puzzle solution, different auxiliary values
        self._seen.add(key)
        if self._accept is not None and not self._accept(values):
            return
        self.solutions.append(self._decode(values))
        if len(self.solutions) >= self._limit:
            self.stop_search()


def enumerate_solutions[T](
    model: cp_model.CpModel,
    variables: Sequence[cp_model.IntVar],
    *,
    limit: int = 2,
    decode: Callable[[list[int]], T],
    accept: Callable[[list[int]], bool] | None = None,
) -> list[T]:
    """Enumerate up to ``limit`` solutions, decoded via ``decode``.

    ``variables`` defines solution identity: two solutions are distinct iff
    they differ on at least one of these variables (assignments differing
    only in auxiliary variables are deduplicated).  ``accept`` lets a module
    impose constraints CP-SAT cannot express directly — a rejected
    assignment is not counted (e.g. connectivity for bridges puzzles).
    """
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    collector = _Collector(variables, limit, decode, accept)
    solver.solve(model, collector)
    return collector.solutions

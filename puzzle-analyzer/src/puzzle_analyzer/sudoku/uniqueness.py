"""Solution counting for sudoku, built on the shared CP-SAT core."""

from collections.abc import Sequence

from ..core import CpModelBuilder, enumerate_solutions
from .grid import BOXES


def count_solutions(values: Sequence[int], limit: int = 2) -> list[list[int]]:
    """Return up to ``limit`` distinct solutions of the puzzle.

    ``len(result) == 0``: unsolvable; ``== 1``: unique; ``>= 2``: multiple
    solutions (only ``limit`` are enumerated, there may be more).
    """
    builder = CpModelBuilder()
    grid = builder.int_grid(9, 9, 1, 9)
    builder.latin_square(grid)
    for box in BOXES:
        builder.model.add_all_different([grid[i // 9][i % 9] for i in box])
    builder.fix_givens(grid, [list(values[r * 9 : r * 9 + 9]) for r in range(9)])

    flat = [grid[r][c] for r in range(9) for c in range(9)]
    return enumerate_solutions(
        builder.model, flat, limit=limit, decode=lambda vals: vals
    )


def is_unique(values: Sequence[int]) -> bool:
    return len(count_solutions(values, limit=2)) == 1

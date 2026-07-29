"""Solution counting for (variant) sudoku, on the shared CP-SAT core."""

from collections.abc import Sequence

from ..core import CpModelBuilder, enumerate_solutions
from .model import SudokuPuzzle, king_pairs, knight_pairs
from .solver import as_puzzle


def count_solutions(
    values: Sequence[int] | SudokuPuzzle, limit: int = 2
) -> list[list[int]]:
    """Return up to ``limit`` distinct solutions of the puzzle.

    ``len(result) == 0``: unsolvable; ``== 1``: unique; ``>= 2``: multiple
    solutions (only ``limit`` are enumerated, there may be more).
    """
    puzzle = as_puzzle(values)
    builder = CpModelBuilder()
    model = builder.model
    grid = builder.int_grid(9, 9, 1, 9)
    flat = [grid[r][c] for r in range(9) for c in range(9)]

    for unit in puzzle.geometry.units:
        model.add_all_different([flat[i] for i in unit])
    pairs = []
    if puzzle.variants.antiknight:
        pairs += knight_pairs()
    if puzzle.variants.antiking:
        pairs += king_pairs()
    for a, b in pairs:
        model.add(flat[a] != flat[b])
    for cage in puzzle.variants.cages:
        members = [flat[i] for i in cage.cells]
        model.add(sum(members) == cage.total)
        model.add_all_different(members)
    for i, v in enumerate(puzzle.values):
        if v:
            model.add(flat[i] == v)

    return enumerate_solutions(model, flat, limit=limit, decode=lambda v: v)


def is_unique(values: Sequence[int] | SudokuPuzzle) -> bool:
    return len(count_solutions(values, limit=2)) == 1

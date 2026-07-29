"""Mutable board state: cell values plus pencil-mark candidates.

The board carries its :class:`~puzzle_analyzer.sudoku.grid.Geometry` (and
killer cages, when present) so the techniques operate on whatever units
and peers the variant defines, not on hardcoded classic constants.
"""

from collections.abc import Sequence
from typing import Self

from .grid import ALL_CELLS, CLASSIC, DIGITS, Geometry, cell_name
from .model import Cage


class Board:
    """A partially solved grid with maintained candidate sets.

    ``values[i]`` is 0 for an unsolved cell.  ``candidates[i]`` is the set
    of digits still possible in cell ``i`` (empty set for solved cells).
    """

    def __init__(
        self,
        values: Sequence[int],
        geometry: Geometry = CLASSIC,
        cages: tuple[Cage, ...] = (),
    ):
        self.geometry = geometry
        self.cages = cages
        self.values: list[int] = list(values)
        self.candidates: list[set[int]] = []
        for i in ALL_CELLS:
            if self.values[i]:
                self.candidates.append(set())
            else:
                used = {
                    self.values[p]
                    for p in geometry.peers[i]
                    if self.values[p]
                }
                self.candidates.append(set(DIGITS) - used)

    def place(self, cell: int, digit: int) -> None:
        self.values[cell] = digit
        self.candidates[cell] = set()
        for peer in self.geometry.peers[cell]:
            self.candidates[peer].discard(digit)

    def eliminate(self, cell: int, digit: int) -> None:
        self.candidates[cell].discard(digit)

    def is_solved(self) -> bool:
        return all(self.values)

    def unsolved_cells(self) -> list[int]:
        return [i for i in ALL_CELLS if not self.values[i]]

    def find_contradiction(self) -> str | None:
        """Return a description of a dead-end state, or None if consistent."""
        for i in ALL_CELLS:
            if not self.values[i] and not self.candidates[i]:
                return f"{cell_name(i)} has no remaining candidates"
        return None

    def copy(self) -> Self:
        clone = Board.__new__(Board)
        clone.geometry = self.geometry
        clone.cages = self.cages
        clone.values = list(self.values)
        clone.candidates = [set(c) for c in self.candidates]
        return clone

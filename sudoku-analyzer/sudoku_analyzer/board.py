"""Mutable board state: cell values plus pencil-mark candidates."""

from __future__ import annotations

from typing import List, Optional, Sequence, Set

from .grid import ALL_CELLS, DIGITS, PEERS, cell_name


class Board:
    """A partially solved grid with maintained candidate sets.

    ``values[i]`` is 0 for an unsolved cell.  ``candidates[i]`` is the set of
    digits still possible in cell ``i`` (empty set for solved cells).
    """

    def __init__(self, values: Sequence[int]):
        self.values: List[int] = list(values)
        self.candidates: List[Set[int]] = []
        for i in ALL_CELLS:
            if self.values[i]:
                self.candidates.append(set())
            else:
                used = {self.values[p] for p in PEERS[i] if self.values[p]}
                self.candidates.append(set(DIGITS) - used)

    def place(self, cell: int, digit: int) -> None:
        self.values[cell] = digit
        self.candidates[cell] = set()
        for peer in PEERS[cell]:
            self.candidates[peer].discard(digit)

    def eliminate(self, cell: int, digit: int) -> None:
        self.candidates[cell].discard(digit)

    def is_solved(self) -> bool:
        return all(self.values)

    def unsolved_cells(self) -> List[int]:
        return [i for i in ALL_CELLS if not self.values[i]]

    def find_contradiction(self) -> Optional[str]:
        """Return a description of a dead-end state, or None if consistent."""
        for i in ALL_CELLS:
            if not self.values[i] and not self.candidates[i]:
                return f"{cell_name(i)} has no remaining candidates"
        return None

    def copy(self) -> "Board":
        clone = Board.__new__(Board)
        clone.values = list(self.values)
        clone.candidates = [set(c) for c in self.candidates]
        return clone

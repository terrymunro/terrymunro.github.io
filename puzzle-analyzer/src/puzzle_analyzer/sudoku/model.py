"""The variant sudoku model: a grid plus optional extra constraints.

Supported variants (freely composable):

* ``diagonal_down`` / ``diagonal_up`` — digits on the main diagonals must
  differ (both together = Sudoku X).
* ``antiknight`` / ``antiking`` — cells a chess knight's/king's move apart
  must differ.
* ``cages`` — killer cages: the cells sum to a target and hold distinct
  digits (classic sudoku rules still apply on top).
* ``extra_regions`` — additional 9-cell all-different regions (windoku,
  extra-region sudoku).

JSON spec format (all variant fields optional)::

    {
      "givens": "530070000...",            # 81 chars, 0/. for blanks
      "diagonal_down": true,
      "diagonal_up": true,
      "antiknight": true,
      "antiking": false,
      "cages": [{"cells": [[0, 0], [0, 1]], "sum": 12}, ...],
      "extra_regions": [[[1, 1], [1, 2], ...], ...]
    }

A bare 81-character string still means a classic puzzle.
"""

import functools
from dataclasses import dataclass, field
from typing import Any

from ..core.spec import SpecError, get_field
from .grid import (
    ALL_CELLS,
    CLASSIC,
    Geometry,
    build_geometry,
    cell_name,
    col_of,
    parse_puzzle,
    row_of,
)

#: Cell indices of the two main diagonals.
DIAGONAL_DOWN = tuple(r * 9 + r for r in range(9))  # R1C1 .. R9C9
DIAGONAL_UP = tuple(r * 9 + (8 - r) for r in range(9))  # R9C1 .. R1C9


@dataclass(frozen=True, slots=True)
class Cage:
    """A killer cage: distinct digits in ``cells`` summing to ``total``."""

    cells: tuple[int, ...]
    total: int


@dataclass(frozen=True, slots=True)
class Variants:
    diagonal_down: bool = False
    diagonal_up: bool = False
    antiknight: bool = False
    antiking: bool = False
    cages: tuple[Cage, ...] = ()
    extra_regions: tuple[tuple[int, ...], ...] = ()

    @property
    def is_classic(self) -> bool:
        return self == Variants()

    def describe(self) -> list[str]:
        parts = []
        if self.diagonal_down and self.diagonal_up:
            parts.append("Sudoku X (both diagonals)")
        elif self.diagonal_down or self.diagonal_up:
            parts.append("one diagonal")
        if self.antiknight:
            parts.append("anti-knight")
        if self.antiking:
            parts.append("anti-king")
        if self.cages:
            parts.append(f"killer ({len(self.cages)} cages)")
        if self.extra_regions:
            parts.append(f"{len(self.extra_regions)} extra regions")
        return parts


@dataclass(frozen=True, slots=True)
class SudokuPuzzle:
    values: tuple[int, ...]
    variants: Variants = field(default_factory=Variants)

    @property
    def geometry(self) -> Geometry:
        return geometry_for(self.variants)


def _leaper_pairs(offsets: list[tuple[int, int]]) -> list[tuple[int, int]]:
    pairs = []
    for cell in ALL_CELLS:
        r, c = row_of(cell), col_of(cell)
        for dr, dc in offsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 9 and 0 <= cc < 9:
                pairs.append((cell, rr * 9 + cc))
    return pairs


def knight_pairs() -> list[tuple[int, int]]:
    return _leaper_pairs([(-2, 1), (-1, 2), (1, 2), (2, 1)])


def king_pairs() -> list[tuple[int, int]]:
    # Orthogonal neighbours already share a row/column; only the diagonal
    # touches add anything.
    return _leaper_pairs([(1, 1), (1, -1)])


@functools.lru_cache(maxsize=64)
def geometry_for(variants: Variants) -> Geometry:
    if variants.is_classic:
        return CLASSIC
    extra_units: list[tuple[str, tuple[int, ...]]] = []
    if variants.diagonal_down:
        extra_units.append(("diagonal R1C1-R9C9", DIAGONAL_DOWN))
    if variants.diagonal_up:
        extra_units.append(("diagonal R9C1-R1C9", DIAGONAL_UP))
    for index, region in enumerate(variants.extra_regions, 1):
        extra_units.append((f"extra region {index}", region))
    pairs: list[tuple[int, int]] = []
    if variants.antiknight:
        pairs += knight_pairs()
    if variants.antiking:
        pairs += king_pairs()
    return build_geometry(extra_units, pairs)


def _parse_cells(raw: list[Any], context: str) -> tuple[int, ...]:
    cells = []
    for entry in raw:
        r, c = int(entry[0]), int(entry[1])
        if not (0 <= r < 9 and 0 <= c < 9):
            raise SpecError(f"{context}: cell ({r},{c}) is outside the grid")
        cells.append(r * 9 + c)
    return tuple(cells)


def _parse_givens(givens: Any) -> tuple[int, ...]:
    if isinstance(givens, str):
        return tuple(parse_puzzle(givens))
    values = []
    for v in givens:
        # Exact integers only: int(1.9) would silently certify a different
        # puzzle than the one supplied, and bool is not a digit.
        if isinstance(v, bool) or not isinstance(v, int):
            raise SpecError(f"givens must be integral digits 0-9, got {v!r}")
        values.append(v)
    if len(values) != 81:
        raise SpecError(f"givens must have 81 cells, got {len(values)}")
    if bad := [v for v in values if not 0 <= v <= 9]:
        raise SpecError(f"givens must be digits 0-9, got {sorted(set(bad))}")
    return tuple(values)


def parse_spec(spec: dict[str, Any]) -> SudokuPuzzle:
    """Build a puzzle from the JSON object form."""
    values = _parse_givens(spec.get("givens", "." * 81))
    cages = tuple(
        Cage(
            cells=_parse_cells(get_field(raw, "cells", list), "cage"),
            total=get_field(raw, "sum", int),
        )
        for raw in get_field(spec, "cages", list, [], required=False)
    )
    regions = tuple(
        _parse_cells(raw, "extra region")
        for raw in get_field(spec, "extra_regions", list, [], required=False)
    )
    return SudokuPuzzle(
        values=values,
        variants=Variants(
            diagonal_down=bool(spec.get("diagonal_down", False)),
            diagonal_up=bool(spec.get("diagonal_up", False)),
            antiknight=bool(spec.get("antiknight", False)),
            antiking=bool(spec.get("antiking", False)),
            cages=cages,
            extra_regions=regions,
        ),
    )


def _cage_sum_bounds(size: int) -> tuple[int, int]:
    return size * (size + 1) // 2, size * (19 - size) // 2


def find_conflicts(puzzle: SudokuPuzzle) -> list[str]:
    """All rule violations among the givens, plus malformed cages."""
    geometry = puzzle.geometry
    values = puzzle.values
    conflicts = []
    for unit_index, unit in enumerate(geometry.units):
        seen: dict[int, int] = {}
        for cell in unit:
            v = values[cell]
            if not v:
                continue
            if v in seen:
                conflicts.append(
                    f"digit {v} appears at both {cell_name(seen[v])} and "
                    f"{cell_name(cell)} in {geometry.unit_names[unit_index]}"
                )
            else:
                seen[v] = cell
    pair_rules = []
    if puzzle.variants.antiknight:
        pair_rules.append(("a knight's move apart", knight_pairs()))
    if puzzle.variants.antiking:
        pair_rules.append(("a king's move apart", king_pairs()))
    for label, pairs in pair_rules:
        for a, b in pairs:
            if values[a] and values[a] == values[b]:
                conflicts.append(
                    f"digit {values[a]} at {cell_name(a)} and {cell_name(b)} "
                    f"are {label}"
                )
    seen_in_cages: set[int] = set()
    for index, cage in enumerate(puzzle.variants.cages, 1):
        name = f"cage {index} (sum {cage.total})"
        if not 1 <= len(cage.cells) <= 9:
            conflicts.append(f"{name}: must have 1-9 cells")
            continue
        for cell in cage.cells:
            if cell in seen_in_cages:
                conflicts.append(f"{name}: {cell_name(cell)} is in two cages")
            seen_in_cages.add(cell)
        lo, hi = _cage_sum_bounds(len(cage.cells))
        if not lo <= cage.total <= hi:
            conflicts.append(
                f"{name}: sum must be {lo}..{hi} for {len(cage.cells)} cells"
            )
        given = [values[c] for c in cage.cells if values[c]]
        if len(set(given)) != len(given):
            conflicts.append(f"{name}: repeated given digit inside the cage")
    for index, region in enumerate(puzzle.variants.extra_regions, 1):
        if len(region) != 9 or len(set(region)) != 9:
            conflicts.append(f"extra region {index}: must be 9 distinct cells")
    return conflicts

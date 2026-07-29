"""Grid parsing, formatting and static geometry for 9x9 sudoku.

Cells are indexed 0..80, row-major.  Rows, columns and boxes are numbered
1..9 in human-readable output (boxes left-to-right, top-to-bottom).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

DIGITS = tuple(range(1, 10))
ALL_CELLS = tuple(range(81))


def row_of(cell: int) -> int:
    return cell // 9


def col_of(cell: int) -> int:
    return cell % 9


def box_of(cell: int) -> int:
    return (cell // 27) * 3 + (cell % 9) // 3


ROWS: List[List[int]] = [[r * 9 + c for c in range(9)] for r in range(9)]
COLS: List[List[int]] = [[r * 9 + c for r in range(9)] for c in range(9)]
BOXES: List[List[int]] = [
    [(br * 3 + r) * 9 + (bc * 3 + c) for r in range(3) for c in range(3)]
    for br in range(3)
    for bc in range(3)
]

#: All 27 units.  Order matters for deterministic solver output:
#: rows 1-9, columns 1-9, boxes 1-9.
UNITS: List[List[int]] = ROWS + COLS + BOXES
UNIT_NAMES: List[str] = (
    [f"row {i + 1}" for i in range(9)]
    + [f"column {i + 1}" for i in range(9)]
    + [f"box {i + 1}" for i in range(9)]
)

#: For each cell, the indices (into UNITS) of the 3 units containing it.
CELL_UNITS: List[List[int]] = [
    [row_of(i), 9 + col_of(i), 18 + box_of(i)] for i in ALL_CELLS
]

#: For each cell, the 20 other cells sharing a row, column or box with it.
PEERS: List[frozenset] = [
    frozenset(
        peer
        for unit_index in CELL_UNITS[i]
        for peer in UNITS[unit_index]
        if peer != i
    )
    for i in ALL_CELLS
]


def cell_name(cell: int) -> str:
    return f"R{row_of(cell) + 1}C{col_of(cell) + 1}"


def cells_name(cells: Iterable[int]) -> str:
    return ",".join(cell_name(c) for c in sorted(cells))


def parse_puzzle(text: str) -> List[int]:
    """Parse a puzzle from a string.

    Accepts 81 significant characters where 1-9 are givens and 0/./x/_ are
    blanks.  Whitespace, newlines and ASCII grid decorations (|+-) are
    ignored, so both one-line strings and pretty-printed grids work.
    """
    values: List[int] = []
    for ch in text:
        if ch in "123456789":
            values.append(int(ch))
        elif ch in "0.x_*":
            values.append(0)
        elif ch.isspace() or ch in "|+-":
            continue
        else:
            raise ValueError(f"unexpected character in puzzle: {ch!r}")
    if len(values) != 81:
        raise ValueError(f"puzzle must contain 81 cells, found {len(values)}")
    return values


def to_line(values: Sequence[int]) -> str:
    """Serialise a grid to the canonical 81-character one-line form."""
    return "".join(str(v) if v else "." for v in values)


def format_grid(values: Sequence[int]) -> str:
    """Pretty-print a grid with box separators."""
    lines = []
    for r in range(9):
        if r in (3, 6):
            lines.append("------+-------+------")
        row = []
        for c in range(9):
            if c in (3, 6):
                row.append("|")
            v = values[r * 9 + c]
            row.append(str(v) if v else ".")
        lines.append(" ".join(row))
    return "\n".join(lines)


def find_given_conflicts(values: Sequence[int]) -> List[str]:
    """Return human-readable descriptions of duplicated givens, if any."""
    conflicts = []
    for unit_index, unit in enumerate(UNITS):
        seen = {}
        for cell in unit:
            v = values[cell]
            if not v:
                continue
            if v in seen:
                conflicts.append(
                    f"digit {v} appears at both {cell_name(seen[v])} and "
                    f"{cell_name(cell)} in {UNIT_NAMES[unit_index]}"
                )
            else:
                seen[v] = cell
    return conflicts

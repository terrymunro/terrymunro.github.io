"""Grid parsing, formatting and static geometry for 9x9 sudoku.

Cells are indexed 0..80, row-major.  Rows, columns and boxes are numbered
1..9 in human-readable output (boxes left-to-right, top-to-bottom).
"""

from collections.abc import Iterable, Sequence

DIGITS = tuple(range(1, 10))
ALL_CELLS = tuple(range(81))


def row_of(cell: int) -> int:
    return cell // 9


def col_of(cell: int) -> int:
    return cell % 9


def box_of(cell: int) -> int:
    return (cell // 27) * 3 + (cell % 9) // 3


ROWS: list[list[int]] = [[r * 9 + c for c in range(9)] for r in range(9)]
COLS: list[list[int]] = [[r * 9 + c for r in range(9)] for c in range(9)]
BOXES: list[list[int]] = [
    [(br * 3 + r) * 9 + (bc * 3 + c) for r in range(3) for c in range(3)]
    for br in range(3)
    for bc in range(3)
]

#: All 27 units.  Order matters for deterministic solver output:
#: rows 1-9, columns 1-9, boxes 1-9.
UNITS: list[list[int]] = ROWS + COLS + BOXES
UNIT_NAMES: list[str] = (
    [f"row {i + 1}" for i in range(9)]
    + [f"column {i + 1}" for i in range(9)]
    + [f"box {i + 1}" for i in range(9)]
)

#: For each cell, the indices (into UNITS) of the 3 units containing it.
CELL_UNITS: list[list[int]] = [
    [row_of(i), 9 + col_of(i), 18 + box_of(i)] for i in ALL_CELLS
]

#: For each cell, the 20 other cells sharing a row, column or box with it.
PEERS: list[frozenset] = [
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


def parse_puzzle(text: str) -> list[int]:
    """Parse a puzzle from a string.

    Accepts 81 significant characters where 1-9 are givens and 0/./x/_ are
    blanks.  Whitespace, newlines and ASCII grid decorations (|+-) are
    ignored, so both one-line strings and pretty-printed grids work.
    """
    values: list[int] = []
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


def find_given_conflicts(values: Sequence[int]) -> list[str]:
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


# --------------------------------------------------------------------------
# Instance geometry (variant support)
# --------------------------------------------------------------------------

from dataclasses import dataclass as _dataclass  # noqa: E402


@_dataclass(frozen=True, slots=True)
class Geometry:
    """The complete constraint geometry of one puzzle instance.

    The first 27 units are always the classic rows, columns and boxes (in
    that order — the fish techniques rely on it); variants append extra
    all-different units (diagonals, extra regions) and extra peer pairs
    (anti-knight, anti-king).
    """

    units: tuple[tuple[int, ...], ...]
    unit_names: tuple[str, ...]
    peers: tuple[frozenset[int], ...]
    cell_units: tuple[tuple[int, ...], ...]


def build_geometry(
    extra_units: Sequence[tuple[str, Sequence[int]]] = (),
    extra_peer_pairs: Sequence[tuple[int, int]] = (),
) -> Geometry:
    """Classic geometry plus named extra units and extra peer pairs."""
    units = tuple(tuple(u) for u in UNITS) + tuple(
        tuple(cells) for _, cells in extra_units
    )
    unit_names = tuple(UNIT_NAMES) + tuple(name for name, _ in extra_units)
    cell_units = tuple(
        tuple(k for k, unit in enumerate(units) if i in unit) for i in ALL_CELLS
    )
    peer_sets: list[set[int]] = [set() for _ in ALL_CELLS]
    for unit in units:
        for cell in unit:
            peer_sets[cell].update(c for c in unit if c != cell)
    for a, b in extra_peer_pairs:
        peer_sets[a].add(b)
        peer_sets[b].add(a)
    return Geometry(
        units=units,
        unit_names=unit_names,
        peers=tuple(frozenset(p) for p in peer_sets),
        cell_units=cell_units,
    )


#: The plain 9x9 sudoku geometry.
CLASSIC = build_geometry()

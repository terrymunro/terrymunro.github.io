"""Human solving techniques.

Each finder inspects a :class:`~sudoku_analyzer.board.Board` and returns the
first :class:`Step` it can justify, or ``None``.  Finders never mutate the
board; the solver applies the step's placements/eliminations afterwards.

Implemented repertoire, roughly in order of difficulty:

* Naked / Hidden Single
* Locked Candidates (pointing and claiming)
* Naked / Hidden Pair, Triple, Quad
* Basic fish: X-Wing, Swordfish, Jellyfish
* XY-Wing, XYZ-Wing

Anything a puzzle needs beyond this repertoire is reported as requiring
chains or trial-and-error ("guessing").
"""

import itertools
from collections.abc import Callable
from dataclasses import dataclass, field

from .board import Board
from .grid import (
    BOXES,
    COLS,
    DIGITS,
    PEERS,
    ROWS,
    UNIT_NAMES,
    UNITS,
    box_of,
    cell_name,
    cells_name,
    col_of,
    row_of,
)

type Placement = tuple[int, int]  # (cell, digit)
type Elimination = tuple[int, int]  # (cell, digit)


@dataclass(slots=True)
class Step:
    """One annotated solving step."""

    technique: str
    description: str
    placements: list[Placement] = field(default_factory=list)
    eliminations: list[Elimination] = field(default_factory=list)


def _format_eliminations(eliminations: list[Elimination]) -> str:
    by_digit: dict = {}
    for cell, digit in eliminations:
        by_digit.setdefault(digit, []).append(cell)
    parts = [
        f"{digit} from {cells_name(cells)}"
        for digit, cells in sorted(by_digit.items())
    ]
    return "; ".join(parts)


# --------------------------------------------------------------------------
# Singles
# --------------------------------------------------------------------------

def find_naked_single(board: Board) -> Step | None:
    for cell in board.unsolved_cells():
        if len(board.candidates[cell]) == 1:
            digit = next(iter(board.candidates[cell]))
            return Step(
                technique="Naked Single",
                description=(
                    f"{cell_name(cell)} must be {digit} — it is the only "
                    f"candidate left in that cell"
                ),
                placements=[(cell, digit)],
            )
    return None


def find_hidden_single(board: Board) -> Step | None:
    for unit_index, unit in enumerate(UNITS):
        for digit in DIGITS:
            spots = [c for c in unit if digit in board.candidates[c]]
            if len(spots) == 1:
                cell = spots[0]
                return Step(
                    technique="Hidden Single",
                    description=(
                        f"{cell_name(cell)} must be {digit} — it is the only "
                        f"cell in {UNIT_NAMES[unit_index]} that can take {digit}"
                    ),
                    placements=[(cell, digit)],
                )
    return None


# --------------------------------------------------------------------------
# Locked candidates
# --------------------------------------------------------------------------

def find_locked_candidates_pointing(board: Board) -> Step | None:
    """All candidates for a digit in a box lie on one line -> clear the line."""
    for box_index, box in enumerate(BOXES):
        for digit in DIGITS:
            spots = [c for c in box if digit in board.candidates[c]]
            if len(spots) < 2:
                continue
            for line_of, lines, kind in (
                (row_of, ROWS, "row"),
                (col_of, COLS, "column"),
            ):
                line_ids = {line_of(c) for c in spots}
                if len(line_ids) != 1:
                    continue
                line_id = line_ids.pop()
                eliminations = [
                    (c, digit)
                    for c in lines[line_id]
                    if box_of(c) != box_index and digit in board.candidates[c]
                ]
                if eliminations:
                    return Step(
                        technique="Locked Candidates (Pointing)",
                        description=(
                            f"in box {box_index + 1}, digit {digit} is "
                            f"confined to {kind} {line_id + 1} "
                            f"({cells_name(spots)}); eliminate "
                            f"{_format_eliminations(eliminations)}"
                        ),
                        eliminations=eliminations,
                    )
    return None


def find_locked_candidates_claiming(board: Board) -> Step | None:
    """All candidates for a digit on a line lie in one box -> clear the box."""
    for lines, kind in ((ROWS, "row"), (COLS, "column")):
        for line_id, line in enumerate(lines):
            for digit in DIGITS:
                spots = [c for c in line if digit in board.candidates[c]]
                if len(spots) < 2:
                    continue
                box_ids = {box_of(c) for c in spots}
                if len(box_ids) != 1:
                    continue
                box_index = box_ids.pop()
                eliminations = [
                    (c, digit)
                    for c in BOXES[box_index]
                    if c not in spots and digit in board.candidates[c]
                ]
                if eliminations:
                    return Step(
                        technique="Locked Candidates (Claiming)",
                        description=(
                            f"in {kind} {line_id + 1}, digit {digit} is "
                            f"confined to box {box_index + 1} "
                            f"({cells_name(spots)}); eliminate "
                            f"{_format_eliminations(eliminations)}"
                        ),
                        eliminations=eliminations,
                    )
    return None


# --------------------------------------------------------------------------
# Naked / hidden subsets
# --------------------------------------------------------------------------

_SUBSET_NAMES = {2: "Pair", 3: "Triple", 4: "Quad"}


def _find_naked_subset(board: Board, size: int) -> Step | None:
    for unit_index, unit in enumerate(UNITS):
        open_cells = [
            c for c in unit if 2 <= len(board.candidates[c]) <= size
        ]
        for combo in itertools.combinations(open_cells, size):
            union = set().union(*(board.candidates[c] for c in combo))
            if len(union) != size:
                continue
            eliminations = [
                (c, d)
                for c in unit
                if c not in combo
                for d in sorted(union & board.candidates[c])
            ]
            if eliminations:
                digits = ",".join(map(str, sorted(union)))
                return Step(
                    technique=f"Naked {_SUBSET_NAMES[size]}",
                    description=(
                        f"cells {cells_name(combo)} in "
                        f"{UNIT_NAMES[unit_index]} contain only "
                        f"{{{digits}}}; eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


def _find_hidden_subset(board: Board, size: int) -> Step | None:
    for unit_index, unit in enumerate(UNITS):
        digit_spots = {
            d: [c for c in unit if d in board.candidates[c]] for d in DIGITS
        }
        usable = [d for d in DIGITS if 2 <= len(digit_spots[d]) <= size]
        for combo in itertools.combinations(usable, size):
            cells = set().union(*(digit_spots[d] for d in combo))
            if len(cells) != size:
                continue
            eliminations = [
                (c, d)
                for c in sorted(cells)
                for d in sorted(board.candidates[c] - set(combo))
            ]
            if eliminations:
                digits = ",".join(map(str, combo))
                return Step(
                    technique=f"Hidden {_SUBSET_NAMES[size]}",
                    description=(
                        f"in {UNIT_NAMES[unit_index]}, digits {{{digits}}} "
                        f"only fit in {cells_name(cells)}; those cells can "
                        f"hold nothing else — eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


def find_naked_pair(board: Board) -> Step | None:
    return _find_naked_subset(board, 2)


def find_naked_triple(board: Board) -> Step | None:
    return _find_naked_subset(board, 3)


def find_naked_quad(board: Board) -> Step | None:
    return _find_naked_subset(board, 4)


def find_hidden_pair(board: Board) -> Step | None:
    return _find_hidden_subset(board, 2)


def find_hidden_triple(board: Board) -> Step | None:
    return _find_hidden_subset(board, 3)


def find_hidden_quad(board: Board) -> Step | None:
    return _find_hidden_subset(board, 4)


# --------------------------------------------------------------------------
# Basic fish (X-Wing, Swordfish, Jellyfish)
# --------------------------------------------------------------------------

_FISH_NAMES = {2: "X-Wing", 3: "Swordfish", 4: "Jellyfish"}


def _find_fish(board: Board, size: int) -> Step | None:
    for digit in DIGITS:
        for base_lines, cover_of, base_kind, cover_kind in (
            (ROWS, col_of, "rows", "columns"),
            (COLS, row_of, "columns", "rows"),
        ):
            candidates_per_line = []
            for line_id, line in enumerate(base_lines):
                spots = [c for c in line if digit in board.candidates[c]]
                if 2 <= len(spots) <= size:
                    candidates_per_line.append((line_id, spots))
            for combo in itertools.combinations(candidates_per_line, size):
                cover_ids = set()
                base_cells = []
                for _, spots in combo:
                    cover_ids.update(cover_of(c) for c in spots)
                    base_cells.extend(spots)
                if len(cover_ids) != size:
                    continue
                base_ids = {line_id for line_id, _ in combo}
                cover_lines = ROWS if cover_kind == "rows" else COLS
                eliminations = [
                    (c, digit)
                    for cover_id in sorted(cover_ids)
                    for c in cover_lines[cover_id]
                    if (row_of(c) if base_kind == "rows" else col_of(c))
                    not in base_ids
                    and digit in board.candidates[c]
                ]
                if eliminations:
                    base_list = ",".join(str(i + 1) for i in sorted(base_ids))
                    cover_list = ",".join(
                        str(i + 1) for i in sorted(cover_ids)
                    )
                    return Step(
                        technique=_FISH_NAMES[size],
                        description=(
                            f"digit {digit} in {base_kind} {base_list} is "
                            f"confined to {cover_kind} {cover_list} "
                            f"({cells_name(base_cells)}); eliminate "
                            f"{_format_eliminations(eliminations)}"
                        ),
                        eliminations=eliminations,
                    )
    return None


def find_x_wing(board: Board) -> Step | None:
    return _find_fish(board, 2)


def find_swordfish(board: Board) -> Step | None:
    return _find_fish(board, 3)


def find_jellyfish(board: Board) -> Step | None:
    return _find_fish(board, 4)


# --------------------------------------------------------------------------
# Wings
# --------------------------------------------------------------------------

def find_xy_wing(board: Board) -> Step | None:
    bivalue = [c for c in board.unsolved_cells() if len(board.candidates[c]) == 2]
    for pivot in bivalue:
        x, y = sorted(board.candidates[pivot])
        pincers = [p for p in PEERS[pivot] if p in bivalue and p != pivot]
        for a, b in itertools.combinations(pincers, 2):
            ca, cb = board.candidates[a], board.candidates[b]
            # Pincers must share exactly one digit z with each other, and
            # each must share a different one of the pivot's digits.
            shared = ca & cb
            if len(shared) != 1:
                continue
            z = next(iter(shared))
            if z in (x, y):
                continue
            if not (({x, z} == ca and {y, z} == cb) or ({y, z} == ca and {x, z} == cb)):
                continue
            targets = (PEERS[a] & PEERS[b]) - {pivot}
            eliminations = [
                (c, z) for c in sorted(targets) if z in board.candidates[c]
            ]
            if eliminations:
                return Step(
                    technique="XY-Wing",
                    description=(
                        f"pivot {cell_name(pivot)} {{{x},{y}}} with pincers "
                        f"{cell_name(a)} {{{','.join(map(str, sorted(ca)))}}} "
                        f"and {cell_name(b)} "
                        f"{{{','.join(map(str, sorted(cb)))}}}: one pincer "
                        f"must be {z}; eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


def find_xyz_wing(board: Board) -> Step | None:
    for pivot in board.unsolved_cells():
        if len(board.candidates[pivot]) != 3:
            continue
        pivot_cands = board.candidates[pivot]
        pincers = [
            p
            for p in PEERS[pivot]
            if len(board.candidates[p]) == 2
            and board.candidates[p] <= pivot_cands
        ]
        for a, b in itertools.combinations(pincers, 2):
            shared = board.candidates[a] & board.candidates[b]
            if len(shared) != 1:
                continue
            if board.candidates[a] | board.candidates[b] != pivot_cands:
                continue
            z = next(iter(shared))
            targets = PEERS[a] & PEERS[b] & PEERS[pivot]
            eliminations = [
                (c, z) for c in sorted(targets) if z in board.candidates[c]
            ]
            if eliminations:
                digits = ",".join(map(str, sorted(pivot_cands)))
                return Step(
                    technique="XYZ-Wing",
                    description=(
                        f"pivot {cell_name(pivot)} {{{digits}}} with pincers "
                        f"{cell_name(a)} and {cell_name(b)}: one of the "
                        f"three cells must be {z}; eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Technique:
    name: str
    cost: float
    finder: Callable[[Board], Step | None]


#: Ordered cheapest-first; the solver always applies the easiest applicable
#: technique, mimicking how a human would work through a puzzle.  Costs feed
#: the difficulty grade.
TECHNIQUES: list[Technique] = [
    Technique("Naked Single", 1.0, find_naked_single),
    Technique("Hidden Single", 1.5, find_hidden_single),
    Technique("Locked Candidates (Pointing)", 2.6, find_locked_candidates_pointing),
    Technique("Locked Candidates (Claiming)", 2.8, find_locked_candidates_claiming),
    Technique("Naked Pair", 3.0, find_naked_pair),
    Technique("Hidden Pair", 3.4, find_hidden_pair),
    Technique("Naked Triple", 3.6, find_naked_triple),
    Technique("Hidden Triple", 4.0, find_hidden_triple),
    Technique("X-Wing", 4.5, find_x_wing),
    Technique("XY-Wing", 4.8, find_xy_wing),
    Technique("XYZ-Wing", 5.0, find_xyz_wing),
    Technique("Naked Quad", 5.2, find_naked_quad),
    Technique("Swordfish", 5.5, find_swordfish),
    Technique("Hidden Quad", 5.6, find_hidden_quad),
    Technique("Jellyfish", 6.0, find_jellyfish),
]

TECHNIQUE_COST = {t.name: t.cost for t in TECHNIQUES}

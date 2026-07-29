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

import functools
import itertools
from collections.abc import Callable
from dataclasses import dataclass, field

from .board import Board
from .grid import (
    COLS,
    DIGITS,
    ROWS,
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
    for unit_index, unit in enumerate(board.geometry.units):
        for digit in DIGITS:
            spots = [c for c in unit if digit in board.candidates[c]]
            if len(spots) == 1:
                cell = spots[0]
                return Step(
                    technique="Hidden Single",
                    description=(
                        f"{cell_name(cell)} must be {digit} — it is the only "
                        f"cell in {board.geometry.unit_names[unit_index]} "
                        f"that can take {digit}"
                    ),
                    placements=[(cell, digit)],
                )
    return None


# --------------------------------------------------------------------------
# Locked candidates
# --------------------------------------------------------------------------

def _locked_label(name_a: str, name_b: str) -> str:
    """Classic naming: box->line is Pointing, line->box is Claiming."""
    a_is_box, b_is_box = name_a.startswith("box"), name_b.startswith("box")
    if a_is_box and not b_is_box:
        return "Locked Candidates (Pointing)"
    if b_is_box and not a_is_box:
        return "Locked Candidates (Claiming)"
    return "Locked Candidates"


def find_locked_candidates(board: Board) -> Step | None:
    """If every place for a digit in unit A lies inside unit B, the digit
    is locked: eliminate it from the rest of B.

    Generalises classic pointing/claiming to any pair of intersecting
    units, so diagonals and extra regions participate automatically.
    """
    geometry = board.geometry
    for a_index, b_index in _intersecting_unit_pairs(geometry):
        unit_a, unit_b = geometry.units[a_index], geometry.units[b_index]
        b_set = set(unit_b)
        for digit in DIGITS:
            spots = [c for c in unit_a if digit in board.candidates[c]]
            if len(spots) < 2 or not all(c in b_set for c in spots):
                continue
            eliminations = [
                (c, digit)
                for c in unit_b
                if c not in spots and digit in board.candidates[c]
            ]
            if eliminations:
                name_a = geometry.unit_names[a_index]
                name_b = geometry.unit_names[b_index]
                return Step(
                    technique=_locked_label(name_a, name_b),
                    description=(
                        f"in {name_a}, digit {digit} is confined to "
                        f"{name_b} ({cells_name(spots)}); eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


@functools.lru_cache(maxsize=8)
def _intersecting_unit_pairs(geometry) -> list[tuple[int, int]]:
    """Ordered unit pairs sharing at least two cells.

    Box->line pairs come first, then line->box, then everything else, so
    classic puzzles see the familiar pointing-before-claiming order.
    """
    pairs = []
    for a, unit_a in enumerate(geometry.units):
        cells_a = set(unit_a)
        for b, unit_b in enumerate(geometry.units):
            if a != b and len(cells_a & set(unit_b)) >= 2:
                pairs.append((a, b))

    def rank(pair: tuple[int, int]) -> int:
        label = _locked_label(
            geometry.unit_names[pair[0]], geometry.unit_names[pair[1]]
        )
        return {
            "Locked Candidates (Pointing)": 0,
            "Locked Candidates (Claiming)": 1,
        }.get(label, 2)

    pairs.sort(key=rank)
    return pairs


# --------------------------------------------------------------------------
# Naked / hidden subsets
# --------------------------------------------------------------------------

_SUBSET_NAMES = {2: "Pair", 3: "Triple", 4: "Quad"}


def _find_naked_subset(board: Board, size: int) -> Step | None:
    for unit_index, unit in enumerate(board.geometry.units):
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
                        f"{board.geometry.unit_names[unit_index]} contain only "
                        f"{{{digits}}}; eliminate "
                        f"{_format_eliminations(eliminations)}"
                    ),
                    eliminations=eliminations,
                )
    return None


def _find_hidden_subset(board: Board, size: int) -> Step | None:
    for unit_index, unit in enumerate(board.geometry.units):
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
                        f"in {board.geometry.unit_names[unit_index]}, "
                        f"digits {{{digits}}} "
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
        peers = board.geometry.peers
        pincers = [p for p in peers[pivot] if p in bivalue and p != pivot]
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
            targets = (peers[a] & peers[b]) - {pivot}
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
        peers = board.geometry.peers
        pincers = [
            p
            for p in peers[pivot]
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
            targets = peers[a] & peers[b] & peers[pivot]
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
# Killer cages
# --------------------------------------------------------------------------

def _cage_supports(domains: list[set[int]], total: int) -> list[set[int]]:
    """Per-cell digits appearing in some distinct-digit assignment summing
    to ``total`` (all empty when no assignment exists)."""
    size = len(domains)
    supports: list[set[int]] = [set() for _ in range(size)]

    def dfs(index: int, used: int, remaining: int, chosen: list[int]) -> None:
        if index == size:
            if remaining == 0:
                for i, digit in enumerate(chosen):
                    supports[i].add(digit)
            return
        cells_left = size - index - 1
        for digit in domains[index]:
            if used & (1 << digit) or digit > remaining:
                continue
            after = remaining - digit
            # Distinct digits 1..9: the leftover cells need at least
            # 1+2+..., at most 9+8+...
            if after < cells_left * (cells_left + 1) // 2:
                continue
            if after > cells_left * (19 - cells_left) // 2:
                continue
            chosen.append(digit)
            dfs(index + 1, used | (1 << digit), after, chosen)
            chosen.pop()

    dfs(0, 0, total, [])
    return supports


def find_cage_combinations(board: Board) -> Step | None:
    """Prune killer-cage cells to digits used by some valid combination."""
    for index, cage in enumerate(board.cages, 1):
        if all(board.values[c] for c in cage.cells):
            continue
        domains = [
            {board.values[c]} if board.values[c] else board.candidates[c]
            for c in cage.cells
        ]
        supports = _cage_supports(domains, cage.total)
        if not any(supports):
            # No valid combination at all: expose the contradiction by
            # clearing the first open cell so the solver reports it.
            dead = next(c for c in cage.cells if not board.values[c])
            return Step(
                technique="Cage Combinations",
                description=(
                    f"cage {index} at {cell_name(min(cage.cells))} has no "
                    f"valid combination summing to {cage.total}"
                ),
                eliminations=[
                    (dead, digit) for digit in sorted(board.candidates[dead])
                ],
            )
        eliminations = [
            (cell, digit)
            for cell, support in zip(cage.cells, supports, strict=True)
            if not board.values[cell]
            for digit in sorted(board.candidates[cell] - support)
        ]
        if eliminations:
            anchor = cell_name(min(cage.cells))
            return Step(
                technique="Cage Combinations",
                description=(
                    f"cage {index} at {anchor} must make {cage.total} from "
                    f"distinct digits; eliminate "
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
    Technique("Locked Candidates", 2.7, find_locked_candidates),
    Technique("Naked Pair", 3.0, find_naked_pair),
    Technique("Cage Combinations", 3.2, find_cage_combinations),
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

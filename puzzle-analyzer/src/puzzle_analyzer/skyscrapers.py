"""Skyscrapers validation.

Spec format::

    {
      "size": 5,
      "top": [0, 0, 4, 2, 0],      # clue per column, looking down
      "bottom": [2, 0, 0, 0, 0],   # looking up
      "left": [0, 1, 0, 0, 3],     # clue per row, looking right
      "right": [1, 0, 0, 0, 2],    # looking left
      "givens": [[0, ...], ...]    # optional pre-filled heights, 0 = blank
    }

``0`` (or ``null``) means no clue on that rim position.  Heights 1..size
form a Latin square; a rim clue counts the buildings visible from that
side (taller buildings hide everything shorter behind them).
"""

from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class Skyscrapers:
    size: int
    top: tuple[int, ...]
    bottom: tuple[int, ...]
    left: tuple[int, ...]
    right: tuple[int, ...]
    givens: tuple[tuple[int, ...], ...]


def parse(spec: dict[str, Any]) -> Skyscrapers:
    size = get_field(spec, "size", int)

    def rim(key: str) -> tuple[int, ...]:
        raw = get_field(spec, key, list, [0] * size, required=False)
        return tuple(0 if v is None else int(v) for v in raw)

    raw_givens = get_field(spec, "givens", list, [], required=False)
    givens = tuple(tuple(int(v) for v in row) for row in raw_givens) or tuple(
        (0,) * size for _ in range(size)
    )
    return Skyscrapers(
        size=size,
        top=rim("top"),
        bottom=rim("bottom"),
        left=rim("left"),
        right=rim("right"),
        givens=givens,
    )


def check(puzzle: Skyscrapers) -> list[str]:
    n = puzzle.size
    issues = []
    if n < 2:
        issues.append("size must be at least 2")
    for name, rim in (
        ("top", puzzle.top),
        ("bottom", puzzle.bottom),
        ("left", puzzle.left),
        ("right", puzzle.right),
    ):
        if len(rim) != n:
            issues.append(f"{name} rim must have {n} entries, got {len(rim)}")
        elif any(clue and not 1 <= clue <= n for clue in rim):
            issues.append(f"{name} rim clues must be between 1 and {n}")
    if len(puzzle.givens) != n or any(len(row) != n for row in puzzle.givens):
        issues.append(f"givens must be a {n}x{n} grid")
    elif any(v and not 1 <= v <= n for row in puzzle.givens for v in row):
        issues.append(f"given heights must be between 1 and {n}")
    if not any(puzzle.top + puzzle.bottom + puzzle.left + puzzle.right) and not any(
        v for row in puzzle.givens for v in row
    ):
        issues.append("puzzle has no clues at all")
    return issues


def _constrain_visibility(
    builder: CpModelBuilder, line: list[cp_model.IntVar], clue: int, tag: str
) -> None:
    """The number of prefix-maxima along ``line`` equals ``clue``."""
    model = builder.model
    n = len(line)
    prefix_max = line[0]
    visible: list[Any] = [1]  # the first building is always visible
    for i in range(1, n):
        taller = model.new_bool_var(f"vis_{tag}_{i}")
        model.add(line[i] > prefix_max).only_enforce_if(taller)
        model.add(line[i] < prefix_max).only_enforce_if(~taller)
        visible.append(taller)
        new_max = model.new_int_var(1, n, f"pmax_{tag}_{i}")
        model.add_max_equality(new_max, [prefix_max, line[i]])
        prefix_max = new_max
    model.add(sum(visible) == clue)


def validate(puzzle: Skyscrapers, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("skyscrapers", issues)

    n = puzzle.size
    builder = CpModelBuilder()
    grid = builder.int_grid(n, n, 1, n)
    builder.latin_square(grid).fix_givens(grid, puzzle.givens)

    for i in range(n):
        row, col = grid[i], [grid[r][i] for r in range(n)]
        for clue, line, tag in (
            (puzzle.left[i], row, f"L{i}"),
            (puzzle.right[i], row[::-1], f"R{i}"),
            (puzzle.top[i], col, f"T{i}"),
            (puzzle.bottom[i], col[::-1], f"B{i}"),
        ):
            if clue:
                _constrain_visibility(builder, line, clue, tag)

    flat = [grid[r][c] for r in range(n) for c in range(n)]
    solutions = enumerate_solutions(
        builder.model,
        flat,
        limit=limit,
        decode=lambda vals: [vals[r * n : r * n + n] for r in range(n)],
    )
    return Verdict(
        puzzle_type="skyscrapers",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

"""KenKen / Calcudoku validation.

Spec format::

    {
      "size": 5,
      "cages": [
        {"cells": [[0, 0], [0, 1]], "op": "*", "target": 2},
        {"cells": [[0, 2], [0, 3]], "label": "7+"},
        {"cells": [[2, 2]], "op": "=", "target": 3}
      ]
    }

A cage may carry either an explicit ``op``/``target`` or a display
``label`` like ``"30×"``, ``"5÷"``, ``"2−"``, ``"7+"`` (ASCII ``* / - +``
work too).  Subtraction and division cages hold exactly two cells and the
operands may be taken in either order.  Cages must partition the grid.
"""

from dataclasses import dataclass
from typing import Any

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import SpecError, get_field

type Cell = tuple[int, int]

_OP_ALIASES = {
    "+": "+",
    "-": "-",
    "−": "-",
    "*": "*",
    "x": "*",
    "×": "*",
    "/": "/",
    "÷": "/",
    "=": "=",
}


@dataclass(frozen=True, slots=True)
class Cage:
    cells: tuple[Cell, ...]
    op: str
    target: int


@dataclass(frozen=True, slots=True)
class KenKen:
    size: int
    cages: tuple[Cage, ...]


def parse_label(label: str) -> tuple[str, int]:
    """Split a display label like ``"30×"`` into ``("*", 30)``."""
    op = _OP_ALIASES.get(label[-1])
    if op is None or not label[:-1].isdigit():
        raise SpecError(f"cannot parse cage label {label!r}")
    return op, int(label[:-1])


def parse(spec: dict[str, Any]) -> KenKen:
    size = get_field(spec, "size", int)
    cages = []
    for raw in get_field(spec, "cages", list):
        cells = tuple((int(r), int(c)) for r, c in get_field(raw, "cells", list))
        if "label" in raw:
            op, target = parse_label(get_field(raw, "label", str))
        else:
            op = _OP_ALIASES.get(get_field(raw, "op", str))
            if op is None:
                raise SpecError(f"unknown cage op {raw['op']!r}")
            target = get_field(raw, "target", int)
        cages.append(Cage(cells=cells, op=op, target=target))
    return KenKen(size=size, cages=tuple(cages))


def check(puzzle: KenKen) -> list[str]:
    n = puzzle.size
    issues = []
    seen: dict[Cell, int] = {}
    for index, cage in enumerate(puzzle.cages, 1):
        name = f"cage {index} ({cage.target}{cage.op})"
        if not cage.cells:
            issues.append(f"{name}: has no cells")
        for cell in cage.cells:
            r, c = cell
            if not (0 <= r < n and 0 <= c < n):
                issues.append(f"{name}: cell {cell} is outside the grid")
            elif cell in seen:
                issues.append(f"{name}: cell {cell} also in cage {seen[cell]}")
            else:
                seen[cell] = index
        match cage.op:
            case "-" | "/" if len(cage.cells) != 2:
                issues.append(f"{name}: needs exactly two cells")
            case "=" if len(cage.cells) != 1:
                issues.append(f"{name}: a given must be a single cell")
            case "=" if not 1 <= cage.target <= n:
                issues.append(f"{name}: given outside 1..{n}")
    missing = n * n - len(seen)
    if missing and not issues:
        issues.append(f"cages do not cover the grid ({missing} cells uncaged)")
    return issues


def _constrain_cage(
    builder: CpModelBuilder, size: int, tag: int, cage: Cage, cells: list[Any]
) -> None:
    model = builder.model
    match cage.op:
        case "=":
            model.add(cells[0] == cage.target)
        case "+":
            model.add(sum(cells) == cage.target)
        case "-":
            # Two cells, either order: |a - b| == target.
            diff = model.new_int_var(1 - size, size - 1, f"diff_{tag}")
            model.add(diff == cells[0] - cells[1])
            model.add_abs_equality(
                model.new_int_var(cage.target, cage.target, f"abs_{tag}"), diff
            )
        case "/":
            either = model.new_bool_var(f"div_{tag}")
            model.add(cells[0] == cage.target * cells[1]).only_enforce_if(either)
            model.add(cells[1] == cage.target * cells[0]).only_enforce_if(~either)
        case "*":
            bound = size ** len(cells)
            product = cells[0]
            for index, cell in enumerate(cells[1:], 1):
                next_product = model.new_int_var(1, bound, f"prod_{tag}_{index}")
                model.add_multiplication_equality(next_product, [product, cell])
                product = next_product
            model.add(product == cage.target)


def validate(puzzle: KenKen, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("kenken", issues)

    n = puzzle.size
    builder = CpModelBuilder()
    grid = builder.int_grid(n, n, 1, n)
    builder.latin_square(grid)
    for tag, cage in enumerate(puzzle.cages):
        _constrain_cage(
            builder, n, tag, cage, [grid[r][c] for r, c in cage.cells]
        )

    flat = [grid[r][c] for r in range(n) for c in range(n)]
    solutions = enumerate_solutions(
        builder.model,
        flat,
        limit=limit,
        decode=lambda vals: [vals[r * n : r * n + n] for r in range(n)],
    )
    return Verdict(
        puzzle_type="kenken",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

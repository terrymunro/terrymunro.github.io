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

import math
from dataclasses import dataclass
from typing import Any

from .core import (
    AllDifferentPropagator,
    CpModelBuilder,
    Csp,
    Rating,
    Reduction,
    TablePropagator,
    Verdict,
    enumerate_solutions,
    grade_csp,
    product_table,
)
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


# --------------------------------------------------------------------------
# Grading and hardening
# --------------------------------------------------------------------------

def _cage_predicate(cage: Cage) -> Any:
    match cage.op:
        case "=":
            return lambda row: row[0] == cage.target
        case "+":
            return lambda row: sum(row) == cage.target
        case "-":
            return lambda row: abs(row[0] - row[1]) == cage.target
        case "/":
            return lambda row: (
                row[0] == cage.target * row[1] or row[1] == cage.target * row[0]
            )
        case _:
            return lambda row: math.prod(row) == cage.target


def _csp(puzzle: KenKen) -> Csp:
    n = puzzle.size
    domains = {
        f"R{r + 1}C{c + 1}": set(range(1, n + 1))
        for r in range(n)
        for c in range(n)
    }
    propagators: list[Any] = []
    for r in range(n):
        propagators.append(
            AllDifferentPropagator(
                f"row {r + 1}",
                [f"R{r + 1}C{c + 1}" for c in range(n)],
                permutation=True,
            )
        )
    for c in range(n):
        propagators.append(
            AllDifferentPropagator(
                f"column {c + 1}",
                [f"R{r + 1}C{c + 1}" for r in range(n)],
                permutation=True,
            )
        )
    for cage in puzzle.cages:
        scope = [f"R{r + 1}C{c + 1}" for r, c in cage.cells]
        # Distinctness inside a cage only applies where the Latin square
        # forces it (same row or column); the table encodes the arithmetic
        # plus those local distinctness facts.
        same_line = [
            (i, j)
            for i in range(len(cage.cells))
            for j in range(i + 1, len(cage.cells))
            if cage.cells[i][0] == cage.cells[j][0]
            or cage.cells[i][1] == cage.cells[j][1]
        ]
        predicate = _cage_predicate(cage)
        propagators.append(
            TablePropagator(
                f"cage {cage.target}{cage.op} at {scope[0]}",
                scope,
                product_table(
                    [range(1, n + 1)] * len(cage.cells),
                    lambda row, p=predicate, sl=same_line: p(row)
                    and all(row[i] != row[j] for i, j in sl),
                ),
            )
        )
    return Csp(domains=domains, propagators=propagators)


def grade(puzzle: KenKen) -> Rating:
    return grade_csp(_csp(puzzle))


def _adjacent_cages(a: Cage, b: Cage) -> bool:
    return any(
        abs(r1 - r2) + abs(c1 - c2) == 1
        for r1, c1 in a.cells
        for r2, c2 in b.cells
    )


def reductions(puzzle: KenKen):
    """Hardening moves: merge two adjacent cages into one additive cage.

    A bigger "+" cage carries strictly less information than the two cages
    it replaces, and the merged target is derived from the (unique)
    solution so the solution grid is preserved by construction — and then
    re-proved by the hardening engine.
    """
    verdict = validate(puzzle)
    if not verdict.unique:
        return
    solution = verdict.solution
    for i, first in enumerate(puzzle.cages):
        for j in range(i + 1, len(puzzle.cages)):
            second = puzzle.cages[j]
            if not _adjacent_cages(first, second):
                continue
            cells = first.cells + second.cells
            target = sum(solution[r][c] for r, c in cells)
            merged = Cage(cells=cells, op="+", target=target)
            cages = (
                *(
                    cage
                    for k, cage in enumerate(puzzle.cages)
                    if k not in (i, j)
                ),
                merged,
            )
            yield Reduction(
                f"merge the {first.target}{first.op} and "
                f"{second.target}{second.op} cages into {target}+",
                KenKen(size=puzzle.size, cages=cages),
            )

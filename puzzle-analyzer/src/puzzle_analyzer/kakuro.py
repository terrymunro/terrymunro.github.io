"""Kakuro (cross-sums) validation.

Spec format::

    {
      "layout": [[0, 0, ...], [0, 1, 1, ...], ...],   # 1 = fillable cell
      "runs": [
        {"dir": "h", "anchor": [1, 3], "len": 2, "sum": 11},
        {"dir": "v", "anchor": [2, 1], "len": 3, "sum": 19}
      ]
    }

``anchor`` is the first fillable cell of the run (row, column,
zero-based).  Every run holds digits 1-9 with no repeats, adding up to
``sum``.
"""

from dataclasses import dataclass
from typing import Any

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import SpecError, get_field

type Cell = tuple[int, int]

#: Feasible sums for a run of k distinct digits 1..9: [k smallest, k largest].
def _sum_bounds(length: int) -> tuple[int, int]:
    smallest = length * (length + 1) // 2
    largest = length * (19 - length) // 2
    return smallest, largest


@dataclass(frozen=True, slots=True)
class Run:
    direction: str  # "h" or "v"
    anchor: Cell
    length: int
    total: int

    def cells(self) -> tuple[Cell, ...]:
        r, c = self.anchor
        if self.direction == "h":
            return tuple((r, c + i) for i in range(self.length))
        return tuple((r + i, c) for i in range(self.length))


@dataclass(frozen=True, slots=True)
class Kakuro:
    layout: tuple[tuple[bool, ...], ...]
    runs: tuple[Run, ...]


def parse(spec: dict[str, Any]) -> Kakuro:
    layout = tuple(
        tuple(bool(v) for v in row) for row in get_field(spec, "layout", list)
    )
    runs = []
    for raw in get_field(spec, "runs", list):
        direction = get_field(raw, "dir", str)
        if direction not in ("h", "v"):
            raise SpecError(f"run dir must be 'h' or 'v', got {direction!r}")
        r, c = get_field(raw, "anchor", list)
        runs.append(
            Run(
                direction=direction,
                anchor=(int(r), int(c)),
                length=get_field(raw, "len", int),
                total=get_field(raw, "sum", int),
            )
        )
    return Kakuro(layout=layout, runs=tuple(runs))


def check(puzzle: Kakuro) -> list[str]:
    issues = []
    height = len(puzzle.layout)
    width = len(puzzle.layout[0]) if height else 0
    if any(len(row) != width for row in puzzle.layout):
        issues.append("layout rows have inconsistent widths")
        return issues

    covered: set[Cell] = set()
    for index, run in enumerate(puzzle.runs, 1):
        name = f"run {index} ({run.total} over {run.length} {run.direction})"
        if not 2 <= run.length <= 9:
            issues.append(f"{name}: length must be 2..9")
            continue
        lo, hi = _sum_bounds(run.length)
        if not lo <= run.total <= hi:
            issues.append(f"{name}: sum must be {lo}..{hi} for that length")
        for r, c in run.cells():
            if not (0 <= r < height and 0 <= c < width) or not puzzle.layout[r][c]:
                issues.append(f"{name}: cell ({r},{c}) is not fillable")
            covered.add((r, c))

    fillable = {
        (r, c)
        for r in range(height)
        for c in range(width)
        if puzzle.layout[r][c]
    }
    if orphans := sorted(fillable - covered):
        issues.append(f"fillable cells not in any run: {orphans}")
    return issues


def validate(puzzle: Kakuro, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("kakuro", issues)

    builder = CpModelBuilder()
    cells = {
        (r, c): builder.model.new_int_var(1, 9, f"cell_{r}_{c}")
        for r, row in enumerate(puzzle.layout)
        for c, fillable in enumerate(row)
        if fillable
    }
    for run in puzzle.runs:
        run_vars = [cells[cell] for cell in run.cells()]
        builder.model.add(sum(run_vars) == run.total)
        builder.model.add_all_different(run_vars)

    order = sorted(cells)
    solutions = enumerate_solutions(
        builder.model,
        [cells[cell] for cell in order],
        limit=limit,
        decode=lambda vals: {
            f"R{r + 1}C{c + 1}": v
            for (r, c), v in zip(order, vals, strict=True)
        },
    )
    return Verdict(
        puzzle_type="kakuro",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

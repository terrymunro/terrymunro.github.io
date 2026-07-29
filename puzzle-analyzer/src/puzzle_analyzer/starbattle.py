"""Star Battle validation.

Spec format::

    {"regions": [[0, 0, 1, ...], ...], "stars": 1}

``regions`` assigns every cell a region id; the grid is square.  Place
``stars`` stars in every row, every column and every region such that no
two stars touch, even diagonally.
"""

from dataclasses import dataclass
from typing import Any

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class StarBattle:
    regions: tuple[tuple[int, ...], ...]
    stars: int

    @property
    def size(self) -> int:
        return len(self.regions)


def parse(spec: dict[str, Any]) -> StarBattle:
    regions = tuple(
        tuple(int(v) for v in row) for row in get_field(spec, "regions", list)
    )
    return StarBattle(
        regions=regions, stars=get_field(spec, "stars", int, 1, required=False)
    )


def check(puzzle: StarBattle) -> list[str]:
    n = puzzle.size
    issues = []
    if n == 0:
        return ["grid is empty"]
    if any(len(row) != n for row in puzzle.regions):
        issues.append("regions grid must be square")
        return issues
    if puzzle.stars < 1:
        issues.append("stars must be at least 1")
    region_ids = {v for row in puzzle.regions for v in row}
    if len(region_ids) != n:
        issues.append(
            f"expected {n} regions (one star each per row/column/region), "
            f"found {len(region_ids)}"
        )
    return issues


def validate(puzzle: StarBattle, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("starbattle", issues)

    n, stars = puzzle.size, puzzle.stars
    builder = CpModelBuilder()
    grid = builder.bool_grid(n, n, "star")
    model = builder.model

    for r in range(n):
        model.add(sum(grid[r]) == stars)
    for c in range(n):
        model.add(sum(grid[r][c] for r in range(n)) == stars)

    by_region: dict[int, list[Any]] = {}
    for r in range(n):
        for c in range(n):
            by_region.setdefault(puzzle.regions[r][c], []).append(grid[r][c])
    for members in by_region.values():
        model.add(sum(members) == stars)

    # No two stars touch: forbid pairs among right, down and both diagonals.
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    model.add(grid[r][c] + grid[rr][cc] <= 1)

    flat = [grid[r][c] for r in range(n) for c in range(n)]
    solutions = enumerate_solutions(
        builder.model,
        flat,
        limit=limit,
        decode=lambda vals: [
            [c for c in range(n) if vals[r * n + c]] for r in range(n)
        ],
    )
    return Verdict(
        puzzle_type="starbattle",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

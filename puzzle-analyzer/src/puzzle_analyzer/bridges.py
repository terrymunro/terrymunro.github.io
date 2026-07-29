"""Bridges (Hashiwokakero) validation.

Spec format::

    {"islands": [{"r": 0, "c": 0, "deg": 3}, ...], "max_bridges": 2}

Islands sit on grid points; ``"deg": null`` marks an island whose degree
is hidden (a "?" island) and imposes no degree constraint.  Bridges run
straight, horizontally or vertically, between two islands with no island
in between; at most
``max_bridges`` (default 2) may join the same pair; bridges may not cross.
Every island's degree must be met exactly and the finished network must be
connected.

Degree and crossing constraints live in the CP-SAT model; connectivity is
checked on each enumerated configuration (union-find), so disconnected
configurations are never counted as solutions.
"""

from dataclasses import dataclass
from typing import Any

from .core import (
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
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class Island:
    row: int
    col: int
    #: None = hidden degree ("?" island): no degree constraint.
    degree: int | None


@dataclass(frozen=True, slots=True)
class Bridges:
    islands: tuple[Island, ...]
    max_bridges: int = 2


@dataclass(frozen=True, slots=True)
class _Edge:
    """A candidate bridge between islands ``a`` and ``b`` (indices)."""

    a: int
    b: int
    horizontal: bool


def parse(spec: dict[str, Any]) -> Bridges:
    islands = tuple(
        Island(
            row=get_field(raw, "r", int),
            col=get_field(raw, "c", int),
            degree=(
                None
                if raw.get("deg") is None
                else get_field(raw, "deg", int)
            ),
        )
        for raw in get_field(spec, "islands", list)
    )
    return Bridges(
        islands=islands,
        max_bridges=get_field(spec, "max_bridges", int, 2, required=False),
    )


def check(puzzle: Bridges) -> list[str]:
    issues = []
    if len(puzzle.islands) < 2:
        issues.append("need at least two islands")
    if puzzle.max_bridges < 1:
        issues.append("max_bridges must be at least 1")
    positions: dict[tuple[int, int], int] = {}
    for index, island in enumerate(puzzle.islands, 1):
        pos = (island.row, island.col)
        if pos in positions:
            issues.append(
                f"islands {positions[pos]} and {index} share cell {pos}"
            )
        positions[pos] = index
        if island.degree is not None and island.degree < 1:
            issues.append(f"island {index}: degree must be at least 1")
    degrees = [i.degree for i in puzzle.islands]
    if None not in degrees and sum(degrees) % 2:  # type: ignore[arg-type]
        issues.append("island degrees sum to an odd number — impossible")
    return issues


def _candidate_edges(puzzle: Bridges) -> list[_Edge]:
    """Aligned island pairs with no island strictly between them."""
    islands = puzzle.islands
    occupied = {(i.row, i.col) for i in islands}
    edges = []
    for a, first in enumerate(islands):
        for b in range(a + 1, len(islands)):
            second = islands[b]
            if first.row == second.row:
                cols = range(min(first.col, second.col) + 1, max(first.col, second.col))
                if not any((first.row, c) in occupied for c in cols):
                    edges.append(_Edge(a, b, horizontal=True))
            elif first.col == second.col:
                rows = range(min(first.row, second.row) + 1, max(first.row, second.row))
                if not any((r, first.col) in occupied for r in rows):
                    edges.append(_Edge(a, b, horizontal=False))
    return edges


def _crosses(puzzle: Bridges, horizontal: _Edge, vertical: _Edge) -> bool:
    islands = puzzle.islands
    h1, h2 = islands[horizontal.a], islands[horizontal.b]
    v1, v2 = islands[vertical.a], islands[vertical.b]
    return (
        min(v1.row, v2.row) < h1.row < max(v1.row, v2.row)
        and min(h1.col, h2.col) < v1.col < max(h1.col, h2.col)
    )


def _is_connected(count: int, links: list[tuple[int, int]]) -> bool:
    parent = list(range(count))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        parent[find(a)] = find(b)
    return len({find(i) for i in range(count)}) == 1


def validate(puzzle: Bridges, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("bridges", issues)

    edges = _candidate_edges(puzzle)
    builder = CpModelBuilder()
    model = builder.model
    counts = [
        model.new_int_var(0, puzzle.max_bridges, f"edge_{e.a}_{e.b}")
        for e in edges
    ]

    for index, island in enumerate(puzzle.islands):
        if island.degree is None:
            continue
        incident = [
            counts[k]
            for k, edge in enumerate(edges)
            if index in (edge.a, edge.b)
        ]
        model.add(sum(incident) == island.degree)

    used = []
    for k, edge in enumerate(edges):
        flag = model.new_bool_var(f"used_{edge.a}_{edge.b}")
        model.add(counts[k] >= 1).only_enforce_if(flag)
        model.add(counts[k] == 0).only_enforce_if(~flag)
        used.append(flag)
    for i, first in enumerate(edges):
        if not first.horizontal:
            continue
        for j, second in enumerate(edges):
            if second.horizontal or not _crosses(puzzle, first, second):
                continue
            model.add(used[i] + used[j] <= 1)

    def connected(values: list[int]) -> bool:
        links = [
            (edges[k].a, edges[k].b) for k, n in enumerate(values) if n > 0
        ]
        return _is_connected(len(puzzle.islands), links)

    solutions = enumerate_solutions(
        model,
        counts,
        limit=limit,
        accept=connected,
        decode=lambda vals: [
            {"a": edges[k].a, "b": edges[k].b, "bridges": n}
            for k, n in enumerate(vals)
            if n > 0
        ],
    )
    return Verdict(
        puzzle_type="bridges",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )


# --------------------------------------------------------------------------
# Grading and hardening
# --------------------------------------------------------------------------

def _csp(puzzle: Bridges) -> Csp:
    """Degree and crossing constraints only.

    Network connectivity is global and cannot be propagated locally; a
    puzzle whose uniqueness rests on connectivity alone will therefore
    grade as Extreme, which errs on the hard side — never the easy side.
    """
    edges = _candidate_edges(puzzle)
    names = [f"bridge {e.a}-{e.b}" for e in edges]
    domains = {
        name: set(range(puzzle.max_bridges + 1)) for name in names
    }
    propagators: list[Any] = []
    for index, island in enumerate(puzzle.islands):
        if island.degree is None:
            continue
        scope = [
            names[k] for k, edge in enumerate(edges) if index in (edge.a, edge.b)
        ]
        propagators.append(
            TablePropagator(
                f"island {index} at ({island.row},{island.col}) "
                f"needs {island.degree}",
                scope,
                product_table(
                    [range(puzzle.max_bridges + 1)] * len(scope),
                    lambda row, degree=island.degree: sum(row) == degree,
                ),
            )
        )
    for i, first in enumerate(edges):
        if not first.horizontal:
            continue
        for j, second in enumerate(edges):
            if second.horizontal or not _crosses(puzzle, first, second):
                continue
            propagators.append(
                TablePropagator(
                    f"bridges {names[i]} and {names[j]} may not cross",
                    [names[i], names[j]],
                    product_table(
                        [range(puzzle.max_bridges + 1)] * 2,
                        lambda row: row[0] == 0 or row[1] == 0,
                    ),
                )
            )
    return Csp(domains=domains, propagators=propagators)


def grade(puzzle: Bridges) -> Rating:
    return grade_csp(_csp(puzzle))


def reductions(puzzle: Bridges):
    """Hardening moves: hide one island's degree (a "?" island)."""
    for index, island in enumerate(puzzle.islands):
        if island.degree is None:
            continue
        islands = (
            *puzzle.islands[:index],
            Island(row=island.row, col=island.col, degree=None),
            *puzzle.islands[index + 1 :],
        )
        yield Reduction(
            f"hide the degree of island {index} at "
            f"({island.row},{island.col})",
            Bridges(islands=islands, max_bridges=puzzle.max_bridges),
        )

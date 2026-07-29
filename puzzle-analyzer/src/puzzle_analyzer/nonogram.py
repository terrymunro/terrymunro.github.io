"""Nonogram (picture logic / griddler) validation.

Spec format::

    {"rows": [[4, 2], [1, 2], ...], "cols": [[2, 2, 2], null, ...]}

Each entry lists the filled-run lengths of that line in order; ``null``
means the clue is unknown (a "destroyed scan") and imposes no constraint;
``[]`` means the line is empty.

Each clued line is a regular-language constraint (``0* 1{a} 0+ 1{b} ... 0*``)
enforced with CP-SAT's automaton constraint.
"""

from dataclasses import dataclass
from typing import Any

from .core import (
    CpModelBuilder,
    Csp,
    Rating,
    Reduction,
    RegularPropagator,
    Verdict,
    enumerate_solutions,
    grade_csp,
)
from .core.spec import get_field

type Clue = tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class Nonogram:
    rows: tuple[Clue, ...]
    cols: tuple[Clue, ...]

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.cols)


def parse(spec: dict[str, Any]) -> Nonogram:
    def clues(key: str) -> tuple[Clue, ...]:
        raw = get_field(spec, key, list)
        return tuple(
            None if line is None else tuple(int(run) for run in line)
            for line in raw
        )

    return Nonogram(rows=clues("rows"), cols=clues("cols"))


def _line_issues(name: str, clue: Clue, length: int) -> list[str]:
    if clue is None:
        return []
    issues = []
    if any(run <= 0 for run in clue):
        issues.append(f"{name}: run lengths must be positive, got {list(clue)}")
    elif sum(clue) + max(len(clue) - 1, 0) > length:
        issues.append(
            f"{name}: runs {list(clue)} cannot fit in {length} cells"
        )
    return issues


def check(puzzle: Nonogram) -> list[str]:
    issues = []
    if not puzzle.rows or not puzzle.cols:
        issues.append("grid must have at least one row and one column")
    for r, clue in enumerate(puzzle.rows):
        issues += _line_issues(f"row {r + 1}", clue, puzzle.width)
    for c, clue in enumerate(puzzle.cols):
        issues += _line_issues(f"column {c + 1}", clue, puzzle.height)
    row_total = [sum(clue) for clue in puzzle.rows if clue is not None]
    col_total = [sum(clue) for clue in puzzle.cols if clue is not None]
    if (
        len(row_total) == puzzle.height
        and len(col_total) == puzzle.width
        and sum(row_total) != sum(col_total)
    ):
        issues.append(
            f"row clues fill {sum(row_total)} cells but column clues fill "
            f"{sum(col_total)} — the clues are inconsistent"
        )
    return issues


def _automaton(clue: tuple[int, ...]) -> tuple[list[tuple[int, int, int]], int]:
    """Deterministic automaton accepting exactly the lines matching ``clue``.

    Returns (transitions, final_state); state 0 is the start.  States walk
    the template ``gap, run1, gap, run2, ..., last-run`` and the final
    state self-loops on blanks.
    """
    if not clue:
        return [(0, 0, 0)], 0
    transitions = [(0, 0, 0)]  # leading blanks
    state = 0
    for index, run in enumerate(clue):
        transitions.append((state, 1, state + 1))  # start the run
        for cell in range(1, run):
            transitions.append((state + cell, 1, state + cell + 1))
        state += run
        if index < len(clue) - 1:
            transitions.append((state, 0, state + 1))  # mandatory separator
            state += 1
            transitions.append((state, 0, state))  # extra blanks
    transitions.append((state, 0, state))  # trailing blanks
    return transitions, state


def validate(puzzle: Nonogram, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("nonogram", issues)

    builder = CpModelBuilder()
    grid = builder.bool_grid(puzzle.height, puzzle.width)

    def constrain(cells: list[Any], clue: Clue) -> None:
        if clue is None:
            return
        transitions, final = _automaton(clue)
        builder.model.add_automaton(cells, 0, [final], transitions)

    for r, clue in enumerate(puzzle.rows):
        constrain(grid[r], clue)
    for c, clue in enumerate(puzzle.cols):
        constrain([grid[r][c] for r in range(puzzle.height)], clue)

    flat = [grid[r][c] for r in range(puzzle.height) for c in range(puzzle.width)]
    solutions = enumerate_solutions(
        builder.model,
        flat,
        limit=limit,
        decode=lambda vals: [
            "".join(str(vals[r * puzzle.width + c]) for c in range(puzzle.width))
            for r in range(puzzle.height)
        ],
    )
    return Verdict(
        puzzle_type="nonogram",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )


# --------------------------------------------------------------------------
# Grading and hardening
# --------------------------------------------------------------------------

def _line_propagator(
    name: str, scope: list[str], clue: tuple[int, ...]
) -> RegularPropagator:
    triples, final = _automaton(clue)
    transitions = {(state, symbol): nxt for state, symbol, nxt in triples}
    return RegularPropagator(name, scope, transitions, 0, [final])


def _csp(puzzle: Nonogram) -> Csp:
    domains = {
        f"R{r + 1}C{c + 1}": {0, 1}
        for r in range(puzzle.height)
        for c in range(puzzle.width)
    }
    propagators = []
    for r, clue in enumerate(puzzle.rows):
        if clue is not None:
            scope = [f"R{r + 1}C{c + 1}" for c in range(puzzle.width)]
            propagators.append(
                _line_propagator(f"row {r + 1} clue {list(clue)}", scope, clue)
            )
    for c, clue in enumerate(puzzle.cols):
        if clue is not None:
            scope = [f"R{r + 1}C{c + 1}" for r in range(puzzle.height)]
            propagators.append(
                _line_propagator(f"column {c + 1} clue {list(clue)}", scope, clue)
            )
    return Csp(domains=domains, propagators=propagators)


def grade(puzzle: Nonogram) -> Rating:
    """Grade by line-consistency propagation depth (see core.grading)."""
    return grade_csp(_csp(puzzle))


def reductions(puzzle: Nonogram):
    """Hardening moves: hide one line clue (a "destroyed scan")."""
    for r, clue in enumerate(puzzle.rows):
        if clue is not None:
            rows = (*puzzle.rows[:r], None, *puzzle.rows[r + 1 :])
            yield Reduction(
                f"hide the clue for row {r + 1}",
                Nonogram(rows=rows, cols=puzzle.cols),
            )
    for c, clue in enumerate(puzzle.cols):
        if clue is not None:
            cols = (*puzzle.cols[:c], None, *puzzle.cols[c + 1 :])
            yield Reduction(
                f"hide the clue for column {c + 1}",
                Nonogram(rows=puzzle.rows, cols=cols),
            )

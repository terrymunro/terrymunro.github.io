"""A generic constraint-propagation engine for grading puzzle difficulty.

Every puzzle type can be decomposed into named variables with finite
domains plus *local* constraints (propagators).  The engine then solves
the way a careful human does:

1. **Propagation** — run every propagator to a fixpoint, assigning
   variables whose domain shrinks to one value.  These are "forced"
   deductions.
2. **Probing** — when propagation stalls, hypothesise ``var = value``,
   propagate, and eliminate the value if it leads to a contradiction
   ("what-if" reasoning, one level deep).
3. **Search** — anything still unresolved needs backtracking search; the
   engine stops and reports it rather than guessing.

How far down this ladder a puzzle drags the solver — and how often — is
the difficulty signal used by :mod:`puzzle_analyzer.core.grading`.

Three propagator families cover every puzzle type in this package:

* :class:`TablePropagator` — explicit allowed-tuples constraints
  (cages, clue relations, visibility lines, statement truth tables).
* :class:`RegularPropagator` — regular-language line constraints
  (nonogram runs), pruned exactly via forward/backward automaton
  reachability without enumerating tuples.
* :class:`AllDifferentPropagator` — pairwise-distinct variables, with
  hidden-single pruning when the constraint is a permutation.
"""

import itertools
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

type Value = Hashable
type VarName = str
type Elimination = tuple[VarName, Value]

#: Guard against accidentally materialising huge constraint tables.
MAX_TABLE_SIZE = 300_000


class Propagator(Protocol):
    name: str
    scope: tuple[VarName, ...]

    def prune(self, domains: dict[VarName, set[Value]]) -> list[Elimination]:
        """Values in scope variables' domains that no longer have support."""
        ...


class TablePropagator:
    """Generalised arc consistency over an explicit list of allowed tuples."""

    def __init__(
        self,
        name: str,
        scope: Sequence[VarName],
        tuples: Iterable[tuple[Value, ...]],
    ) -> None:
        self.name = name
        self.scope = tuple(scope)
        self.tuples = list(tuples)
        if len(self.tuples) > MAX_TABLE_SIZE:
            raise ValueError(
                f"constraint table {name!r} exceeds {MAX_TABLE_SIZE} tuples; "
                f"this puzzle is too large for propagation-based grading"
            )

    def prune(self, domains: dict[VarName, set[Value]]) -> list[Elimination]:
        live = [
            row
            for row in self.tuples
            if all(
                value in domains[var]
                for var, value in zip(self.scope, row, strict=True)
            )
        ]
        if not live:
            # Constraint unsatisfiable: empty the first open domain to
            # signal the contradiction to the engine.
            var = self.scope[0]
            return [(var, value) for value in domains[var]]
        eliminations = []
        for index, var in enumerate(self.scope):
            supported = {row[index] for row in live}
            eliminations += [
                (var, value) for value in domains[var] if value not in supported
            ]
        return eliminations


class RegularPropagator:
    """Exact pruning for a deterministic-automaton line constraint.

    ``transitions`` maps ``(state, symbol) -> state`` with ``start`` as the
    initial state; a line is accepted when the final state is in
    ``finals``.  A symbol survives at position ``i`` iff some state
    reachable from the start over positions ``0..i-1`` steps on it into a
    state that can still reach a final state.
    """

    def __init__(
        self,
        name: str,
        scope: Sequence[VarName],
        transitions: dict[tuple[int, Value], int],
        start: int,
        finals: Iterable[int],
    ) -> None:
        self.name = name
        self.scope = tuple(scope)
        self.transitions = transitions
        self.start = start
        self.finals = frozenset(finals)

    def prune(self, domains: dict[VarName, set[Value]]) -> list[Elimination]:
        n = len(self.scope)
        forward: list[set[int]] = [{self.start}]
        for var in self.scope:
            forward.append(
                {
                    nxt
                    for state in forward[-1]
                    for value in domains[var]
                    if (nxt := self.transitions.get((state, value))) is not None
                }
            )
        backward: list[set[int]] = [set() for _ in range(n + 1)]
        backward[n] = set(self.finals)
        for i in range(n - 1, -1, -1):
            var = self.scope[i]
            backward[i] = {
                state
                for state in forward[i]
                for value in domains[var]
                if self.transitions.get((state, value)) in backward[i + 1]
            }
        eliminations = []
        for i, var in enumerate(self.scope):
            supported = {
                value
                for value in domains[var]
                for state in forward[i]
                if state in backward[i]
                and self.transitions.get((state, value)) in backward[i + 1]
            }
            eliminations += [
                (var, value) for value in domains[var] if value not in supported
            ]
        return eliminations


class AllDifferentPropagator:
    """Pairwise-distinct variables.

    Basic pruning removes every assigned value from the other domains.
    When the constraint is a permutation (as many variables as available
    values) it also applies hidden singles: a value supported by exactly
    one variable is forced there.
    """

    def __init__(
        self,
        name: str,
        scope: Sequence[VarName],
        *,
        permutation: bool = False,
    ) -> None:
        self.name = name
        self.scope = tuple(scope)
        self.permutation = permutation

    def prune(self, domains: dict[VarName, set[Value]]) -> list[Elimination]:
        eliminations = []
        for var in self.scope:
            if len(domains[var]) != 1:
                continue
            value = next(iter(domains[var]))
            eliminations += [
                (other, value)
                for other in self.scope
                if other != var and value in domains[other]
            ]
        if self.permutation:
            values = {v for var in self.scope for v in domains[var]}
            for value in values:
                holders = [var for var in self.scope if value in domains[var]]
                if len(holders) == 1 and len(domains[holders[0]]) > 1:
                    var = holders[0]
                    eliminations += [
                        (var, other)
                        for other in domains[var]
                        if other != value
                    ]
        return eliminations


# ---------------------------------------------------------------------------
# Table-building helpers shared by the puzzle modules
# ---------------------------------------------------------------------------

def product_table(
    domains: Sequence[Iterable[Value]],
    predicate: Callable[[tuple[Value, ...]], bool],
) -> list[tuple[Value, ...]]:
    """All tuples from the cartesian product that satisfy ``predicate``."""
    size = 1
    pools = [list(d) for d in domains]
    for pool in pools:
        size *= max(len(pool), 1)
        if size > MAX_TABLE_SIZE:
            raise ValueError(
                f"constraint table would exceed {MAX_TABLE_SIZE} tuples"
            )
    return [row for row in itertools.product(*pools) if predicate(row)]


def permutation_table(
    values: Iterable[Value],
    length: int,
    predicate: Callable[[tuple[Value, ...]], bool] = lambda _: True,
) -> list[tuple[Value, ...]]:
    """All ``length``-permutations of ``values`` satisfying ``predicate``."""
    return [
        row
        for row in itertools.permutations(values, length)
        if predicate(row)
    ]


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Csp:
    """A puzzle decomposed into variables, domains and local constraints."""

    domains: dict[VarName, set[Value]]
    propagators: list[Propagator]


@dataclass(frozen=True, slots=True)
class Step:
    """One annotated deduction."""

    wave: int
    kind: str  # "assign" | "eliminate" | "probe"
    description: str


@dataclass(slots=True)
class SolveReport:
    solved: bool
    assignment: dict[VarName, Value]
    steps: list[Step] = field(default_factory=list)
    waves: int = 0
    probe_count: int = 0
    #: True when propagation + probing were not enough (search needed).
    stalled: bool = False
    #: Set when the puzzle itself is contradictory.
    contradiction: str | None = None


def _propagate(
    csp: Csp,
    domains: dict[VarName, set[Value]],
    steps: list[Step] | None,
    wave_offset: int,
) -> tuple[int, str | None]:
    """Run all propagators to fixpoint.  Returns (waves, contradiction)."""
    wave = 0
    while True:
        wave += 1
        changed = False
        for propagator in csp.propagators:
            eliminations = propagator.prune(domains)
            if not eliminations:
                continue
            changed = True
            for var, value in eliminations:
                domains[var].discard(value)
                if not domains[var]:
                    return wave, f"no value left for {var}"
            if steps is not None:
                forced = [
                    (var, next(iter(domains[var])))
                    for var in dict.fromkeys(v for v, _ in eliminations)
                    if len(domains[var]) == 1
                ]
                for var, value in forced:
                    steps.append(
                        Step(
                            wave=wave_offset + wave,
                            kind="assign",
                            description=(
                                f"{var} = {value} — forced by {propagator.name}"
                            ),
                        )
                    )
        if not changed:
            return wave - 1, None


def solve(csp: Csp, *, max_probes: int = 2000) -> SolveReport:
    """Solve by propagation and single-level probing; never search."""
    domains = {var: set(values) for var, values in csp.domains.items()}
    steps: list[Step] = []
    waves = 0
    probes = 0

    def solved() -> bool:
        return all(len(d) == 1 for d in domains.values())

    while True:
        ran, contradiction = _propagate(csp, domains, steps, waves)
        waves += ran
        if contradiction:
            return SolveReport(
                solved=False,
                assignment={},
                steps=steps,
                waves=waves,
                probe_count=probes,
                contradiction=contradiction,
            )
        if solved():
            return SolveReport(
                solved=True,
                assignment={v: next(iter(d)) for v, d in domains.items()},
                steps=steps,
                waves=waves,
                probe_count=probes,
            )

        # Probe: try each open value, cheapest domains first, and eliminate
        # the first hypothesis that propagates to a contradiction.
        eliminated = None
        open_vars = sorted(
            (var for var, d in domains.items() if len(d) > 1),
            key=lambda var: (len(domains[var]), var),
        )
        for var in open_vars:
            for value in sorted(domains[var], key=repr):
                if probes >= max_probes:
                    break
                probes += 1
                trial = {v: set(d) for v, d in domains.items()}
                trial[var] = {value}
                _, failure = _propagate(csp, trial, None, waves)
                if failure:
                    eliminated = (var, value, failure)
                    break
            if eliminated or probes >= max_probes:
                break

        if eliminated is None:
            return SolveReport(
                solved=False,
                assignment={},
                steps=steps,
                waves=waves,
                probe_count=probes,
                stalled=True,
            )
        var, value, failure = eliminated
        domains[var].discard(value)
        steps.append(
            Step(
                wave=waves,
                kind="probe",
                description=(
                    f"hypothesis {var} = {value} propagates to a "
                    f"contradiction ({failure}); eliminate it"
                ),
            )
        )

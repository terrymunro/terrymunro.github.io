"""Balance-scale algebra puzzle validation (e.g. "The Assay Room").

A set of symbols carries hidden integer weights; every given balance is
exact (both pans weigh the same).  Weights are drawn from ``min``..``max``
and are pairwise distinct unless ``distinct`` is false.

Spec format::

    {
      "symbols": ["Quill", "Thorn", "Wheel", "Lantern", "Anchor", "Crescent"],
      "min": 1,
      "max": 9,
      "distinct": true,
      "equations": [
        {"left": ["Quill", "Thorn"], "right": ["Lantern", "Anchor"]},
        {"left": ["Quill", "Lantern", "Anchor"], "right": ["Wheel"]}
      ]
    }
"""

from dataclasses import dataclass
from typing import Any

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import get_field


@dataclass(frozen=True, slots=True)
class Equation:
    left: tuple[str, ...]
    right: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Balance:
    symbols: tuple[str, ...]
    minimum: int
    maximum: int
    distinct: bool
    equations: tuple[Equation, ...]


def parse(spec: dict[str, Any]) -> Balance:
    equations = tuple(
        Equation(
            left=tuple(get_field(raw, "left", list)),
            right=tuple(get_field(raw, "right", list)),
        )
        for raw in get_field(spec, "equations", list)
    )
    return Balance(
        symbols=tuple(get_field(spec, "symbols", list)),
        minimum=get_field(spec, "min", int, 1, required=False),
        maximum=get_field(spec, "max", int),
        distinct=get_field(spec, "distinct", bool, True, required=False),
        equations=equations,
    )


def check(puzzle: Balance) -> list[str]:
    issues = []
    if len(set(puzzle.symbols)) != len(puzzle.symbols):
        issues.append("symbol names must be unique")
    span = puzzle.maximum - puzzle.minimum + 1
    if span < 1:
        issues.append("max must be at least min")
    elif puzzle.distinct and len(puzzle.symbols) > span:
        issues.append(
            f"{len(puzzle.symbols)} distinct weights cannot fit in "
            f"{puzzle.minimum}..{puzzle.maximum}"
        )
    known = set(puzzle.symbols)
    for index, equation in enumerate(puzzle.equations, 1):
        for symbol in equation.left + equation.right:
            if symbol not in known:
                issues.append(f"equation {index}: unknown symbol {symbol!r}")
        if not equation.left or not equation.right:
            issues.append(f"equation {index}: both pans must hold something")
    return issues


def validate(puzzle: Balance, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("balance", issues)

    builder = CpModelBuilder()
    weight = {
        symbol: builder.model.new_int_var(
            puzzle.minimum, puzzle.maximum, f"w_{symbol}"
        )
        for symbol in puzzle.symbols
    }
    if puzzle.distinct:
        builder.model.add_all_different(list(weight.values()))
    for equation in puzzle.equations:
        builder.model.add(
            sum(weight[s] for s in equation.left)
            == sum(weight[s] for s in equation.right)
        )

    solutions = enumerate_solutions(
        builder.model,
        [weight[s] for s in puzzle.symbols],
        limit=limit,
        decode=lambda vals: dict(zip(puzzle.symbols, vals, strict=True)),
    )
    return Verdict(
        puzzle_type="balance",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

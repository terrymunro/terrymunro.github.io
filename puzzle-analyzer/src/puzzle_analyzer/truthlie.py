"""Truth-lie sequence puzzle validation (e.g. "False Choir").

An ordered sequence of ``sequence_length`` distinct candidates must make
exactly ``false_count`` of the statements false and the rest true.

Spec format::

    {
      "candidates": ["Ark", "Bell", "Crow", "Dusk", "Echo", "Flint"],
      "sequence_length": 4,
      "false_count": 3,
      "statements": [
        {"kind": "adjacent", "a": "Ark", "b": "Bell"},
        {"kind": "in_slots", "item": "Dusk", "slots": [1, 2]},
        {"kind": "before", "a": "Crow", "b": "Echo"},
        {"kind": "exactly_one_of", "items": ["Ark", "Bell"]},
        {"kind": "slot_one_of", "slot": 3, "items": ["Dusk", "Flint"]}
      ]
    }

Semantics follow the genre convention: a relational or positional claim
about a candidate who is absent from the sequence is false (``adjacent``,
``before``, ``in_slots``); membership claims (``exactly_one_of``) and slot
claims (``slot_one_of``) are always evaluable.

Solutions are counted by exhaustive enumeration of all ordered
selections — exact, and trivially fast at genre sizes (6P4 = 360).  A
statement's truth value is fully determined by the sequence, so a solution
is a sequence, and the false set is derived from it.
"""

from dataclasses import dataclass
from itertools import permutations
from typing import Any

from .core import Verdict
from .core.spec import get_field

type Statement = dict[str, Any]

STATEMENT_KINDS = frozenset(
    {"adjacent", "before", "in_slots", "exactly_one_of", "slot_one_of"}
)


@dataclass(frozen=True, slots=True)
class TruthLie:
    candidates: tuple[str, ...]
    sequence_length: int
    false_count: int
    statements: tuple[Statement, ...]


def parse(spec: dict[str, Any]) -> TruthLie:
    return TruthLie(
        candidates=tuple(get_field(spec, "candidates", list)),
        sequence_length=get_field(spec, "sequence_length", int),
        false_count=get_field(spec, "false_count", int),
        statements=tuple(get_field(spec, "statements", list)),
    )


def check(puzzle: TruthLie) -> list[str]:
    issues = []
    if len(set(puzzle.candidates)) != len(puzzle.candidates):
        issues.append("candidate names must be unique")
    if not 1 <= puzzle.sequence_length <= len(puzzle.candidates):
        issues.append(
            f"sequence_length must be 1..{len(puzzle.candidates)}"
        )
    if not 0 <= puzzle.false_count <= len(puzzle.statements):
        issues.append("false_count must be between 0 and the statement count")
    known = set(puzzle.candidates)
    for index, statement in enumerate(puzzle.statements, 1):
        kind = statement.get("kind")
        if kind not in STATEMENT_KINDS:
            issues.append(f"statement {index}: unknown kind {kind!r}")
            continue
        names = statement.get("items", [])
        names += [statement[k] for k in ("item", "a", "b") if k in statement]
        for name in names:
            if name not in known:
                issues.append(f"statement {index}: unknown candidate {name!r}")
    return issues


def holds(statement: Statement, sequence: tuple[str, ...]) -> bool:
    """Evaluate a statement against a sequence (slots are 1-based)."""
    slot = {name: i + 1 for i, name in enumerate(sequence)}
    match statement["kind"]:
        case "adjacent":
            a, b = slot.get(statement["a"]), slot.get(statement["b"])
            return a is not None and b is not None and abs(a - b) == 1
        case "before":
            a, b = slot.get(statement["a"]), slot.get(statement["b"])
            return a is not None and b is not None and a < b
        case "in_slots":
            position = slot.get(statement["item"])
            return position is not None and position in set(statement["slots"])
        case "exactly_one_of":
            return sum(name in slot for name in statement["items"]) == 1
        case "slot_one_of":
            index = int(statement["slot"]) - 1
            return (
                0 <= index < len(sequence)
                and sequence[index] in set(statement["items"])
            )
        case kind:  # pragma: no cover - rejected by check()
            raise ValueError(f"unknown statement kind {kind!r}")


def false_statements(
    puzzle: TruthLie, sequence: tuple[str, ...]
) -> list[int]:
    """1-based indices of the statements the sequence makes false."""
    return [
        index
        for index, statement in enumerate(puzzle.statements, 1)
        if not holds(statement, sequence)
    ]


def validate(puzzle: TruthLie, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("truthlie", issues)

    solutions = []
    for sequence in permutations(puzzle.candidates, puzzle.sequence_length):
        lies = false_statements(puzzle, sequence)
        if len(lies) == puzzle.false_count:
            solutions.append(
                {"sequence": list(sequence), "false_statements": lies}
            )
            if len(solutions) >= limit:
                break
    return Verdict(
        puzzle_type="truthlie",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

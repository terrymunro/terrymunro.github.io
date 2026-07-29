"""Zebra / logic-grid puzzle validation.

Spec format::

    {
      "slots": 5,
      "categories": {
        "keeper": ["Aster", "Brivel", "Corda", "Dunmar", "Elish"],
        "relic":  ["Ash Bell", "Bone Key", ...]
      },
      "clues": [
        {"kind": "at_end", "item": "Elish"},
        {"kind": "gap", "a": "Elish", "b": "Noon", "between": 2},
        {"kind": "adjacent", "a": "Glass Eye", "b": "Corda"},
        {"kind": "strictly_between", "item": "Dusk",
         "a": "Salt Coin", "b": "Elish"},
        {"kind": "immediately_left", "a": "Matins", "b": "Ash Bell"},
        {"kind": "before", "a": "Aster", "b": "Bone Key"},
        {"kind": "same_slot", "a": "Rook", "b": "Amber"},
        {"kind": "not_same_slot", "a": "Moth", "b": "Sable"},
        {"kind": "at_slot", "item": "Rook", "slot": 4},
        {"kind": "in_slots", "item": "Bell", "slots": [1, 2]}
      ]
    }

Every category has exactly one item per slot (slots are numbered 1..n,
left to right).  Item names must be unique across categories.  ``gap``
counts the slots strictly between the two items; ``before`` and
``immediately_left`` mean lower slot number.
"""

from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from .core import CpModelBuilder, Verdict, enumerate_solutions
from .core.spec import get_field

type Clue = dict[str, Any]

CLUE_KINDS = frozenset(
    {
        "at_end",
        "at_slot",
        "in_slots",
        "gap",
        "adjacent",
        "strictly_between",
        "immediately_left",
        "before",
        "same_slot",
        "not_same_slot",
    }
)


@dataclass(frozen=True, slots=True)
class Zebra:
    slots: int
    categories: dict[str, tuple[str, ...]]
    clues: tuple[Clue, ...]

    def items(self) -> list[str]:
        return [item for items in self.categories.values() for item in items]


def parse(spec: dict[str, Any]) -> Zebra:
    categories = {
        name: tuple(str(item) for item in items)
        for name, items in get_field(spec, "categories", dict).items()
    }
    return Zebra(
        slots=get_field(spec, "slots", int),
        categories=categories,
        clues=tuple(get_field(spec, "clues", list)),
    )


def _clue_items(clue: Clue) -> list[str]:
    return [clue[key] for key in ("item", "a", "b") if key in clue]


def check(puzzle: Zebra) -> list[str]:
    issues = []
    items = puzzle.items()
    if len(set(items)) != len(items):
        issues.append("item names must be unique across categories")
    for name, members in puzzle.categories.items():
        if len(members) != puzzle.slots:
            issues.append(
                f"category {name!r} has {len(members)} items, "
                f"expected {puzzle.slots}"
            )
    known = set(items)
    for index, clue in enumerate(puzzle.clues, 1):
        kind = clue.get("kind")
        if kind not in CLUE_KINDS:
            issues.append(f"clue {index}: unknown kind {kind!r}")
            continue
        for item in _clue_items(clue):
            if item not in known:
                issues.append(f"clue {index}: unknown item {item!r}")
    return issues


def _encode_clue(
    builder: CpModelBuilder,
    index: int,
    clue: Clue,
    position: dict[str, cp_model.IntVar],
    slots: int,
) -> None:
    model = builder.model
    match clue["kind"]:
        case "at_end":
            model.add_linear_expression_in_domain(
                position[clue["item"]],
                cp_model.Domain.from_values([1, slots]),
            )
        case "at_slot":
            model.add(position[clue["item"]] == int(clue["slot"]))
        case "in_slots":
            model.add_linear_expression_in_domain(
                position[clue["item"]],
                cp_model.Domain.from_values([int(s) for s in clue["slots"]]),
            )
        case "gap":
            distance = int(clue["between"]) + 1
            diff = model.new_int_var(1 - slots, slots - 1, f"gap_{index}")
            model.add(diff == position[clue["a"]] - position[clue["b"]])
            model.add_abs_equality(
                model.new_int_var(distance, distance, f"gapabs_{index}"), diff
            )
        case "adjacent":
            diff = model.new_int_var(1 - slots, slots - 1, f"adj_{index}")
            model.add(diff == position[clue["a"]] - position[clue["b"]])
            model.add_abs_equality(
                model.new_int_var(1, 1, f"adjabs_{index}"), diff
            )
        case "strictly_between":
            item = position[clue["item"]]
            first, second = position[clue["a"]], position[clue["b"]]
            ascending = model.new_bool_var(f"btw_{index}")
            model.add(first < item).only_enforce_if(ascending)
            model.add(item < second).only_enforce_if(ascending)
            model.add(second < item).only_enforce_if(~ascending)
            model.add(item < first).only_enforce_if(~ascending)
        case "immediately_left":
            model.add(position[clue["a"]] + 1 == position[clue["b"]])
        case "before":
            model.add(position[clue["a"]] < position[clue["b"]])
        case "same_slot":
            model.add(position[clue["a"]] == position[clue["b"]])
        case "not_same_slot":
            model.add(position[clue["a"]] != position[clue["b"]])


def validate(puzzle: Zebra, *, limit: int = 2) -> Verdict:
    issues = check(puzzle)
    if issues:
        return Verdict.malformed("zebra", issues)

    builder = CpModelBuilder()
    position = {
        item: builder.model.new_int_var(1, puzzle.slots, f"pos_{item}")
        for item in puzzle.items()
    }
    for members in puzzle.categories.values():
        builder.model.add_all_different([position[item] for item in members])
    for index, clue in enumerate(puzzle.clues):
        _encode_clue(builder, index, clue, position, puzzle.slots)

    order = puzzle.items()

    def decode(values: list[int]) -> dict[str, list[str]]:
        placed = dict(zip(order, values, strict=True))
        return {
            name: sorted(members, key=lambda item: placed[item])
            for name, members in puzzle.categories.items()
        }

    solutions = enumerate_solutions(
        builder.model,
        [position[item] for item in order],
        limit=limit,
        decode=decode,
    )
    return Verdict(
        puzzle_type="zebra",
        well_formed=True,
        solution_count=len(solutions),
        solutions=solutions,
    )

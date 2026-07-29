"""Registry mapping puzzle-type names to their module entry points.

Each puzzle module exposes the same two functions —
``parse(spec) -> puzzle`` and ``validate(puzzle, *, limit) -> Verdict`` —
and the registry is the only place that knows them all.  The CLI (and any
other consumer) depends on this indirection, not on the modules, so adding
a puzzle type means writing one cohesive module and one entry below.
"""

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from .core import Verdict


@dataclass(frozen=True, slots=True)
class PuzzleType:
    name: str
    summary: str
    #: Where this puzzle type appears on the site, for discoverability.
    found_in: str
    module_name: str

    def _module(self) -> ModuleType:
        # sys.modules caches this, so repeated access is cheap.
        return importlib.import_module(f".{self.module_name}", __package__)

    @property
    def parse(self) -> Callable[[Any], Any]:
        return self._module().parse

    @property
    def validate(self) -> Callable[..., Verdict]:
        return self._module().validate


def _entry(name: str, module_name: str, summary: str, found_in: str) -> PuzzleType:
    return PuzzleType(name, summary, found_in, module_name)


PUZZLE_TYPES: dict[str, PuzzleType] = {
    t.name: t
    for t in (
        _entry(
            "sudoku",
            "sudoku",
            "9x9 sudoku; also solves, grades and hardens (see the `sudoku` "
            "subcommand)",
            "—",
        ),
        _entry(
            "nonogram",
            "nonogram",
            "picture-logic grid from row/column run clues; clues may be "
            "unknown (destroyed scans)",
            "The Loom (index), Blind Tomography (abyss)",
        ),
        _entry(
            "skyscrapers",
            "skyscrapers",
            "Latin square with visibility counts on the rim",
            "Sluice Row (index)",
        ),
        _entry(
            "kenken",
            "kenken",
            "calcudoku: Latin square with arithmetic cages",
            "Pressure Lattice (abyss)",
        ),
        _entry(
            "kakuro",
            "kakuro",
            "cross-sums: digit runs with sum clues, no repeats in a run",
            "The Apothecary (index)",
        ),
        _entry(
            "starbattle",
            "starbattle",
            "one star per row, column and region; stars never touch",
            "The Aviary (index)",
        ),
        _entry(
            "bridges",
            "bridges",
            "hashiwokakero: connect islands with 1-2 straight, "
            "non-crossing bridges into one network",
            "The Aqueduct (index)",
        ),
        _entry(
            "zebra",
            "zebra",
            "logic grid: assign each category item to a slot from "
            "relational clues",
            "The Reliquary (index), Switchyard Null (abyss)",
        ),
        _entry(
            "truthlie",
            "truthlie",
            "ordered selection where exactly N statements are false",
            "False Choir (abyss)",
        ),
        _entry(
            "cryptogram",
            "cryptogram",
            "monoalphabetic substitution cipher, uniqueness relative to a "
            "wordlist",
            "The Wax Seals (index), Dead Language (abyss)",
        ),
        _entry(
            "wordladder",
            "wordladder",
            "word chain changing one letter per step, uniqueness relative "
            "to a wordlist",
            "The Alchemist's Stair (index)",
        ),
        _entry(
            "balance",
            "balance",
            "distinct integer weights satisfying exact balance equations",
            "The Assay Room (index)",
        ),
    )
}


def get_puzzle_type(name: str) -> PuzzleType:
    try:
        return PUZZLE_TYPES[name]
    except KeyError:
        known = ", ".join(sorted(PUZZLE_TYPES))
        raise ValueError(f"unknown puzzle type {name!r} (known: {known})") from None

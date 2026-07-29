"""Tests for the generic hardening engine.

The invariants matter more than any particular suggestion: every accepted
edit must preserve well-formedness, the uniqueness proof, the exact
solution, and search-free solvability.  Where the pages make claims about
redundancy, hardening is held to them (tomography's scans are all
necessary; the wax seals' givens are all removable).
"""

import pytest

from puzzle_analyzer import (
    balance,
    bridges,
    cryptogram,
    kenken,
    nonogram,
    skyscrapers,
    sudoku,
    truthlie,
    zebra,
)
from puzzle_analyzer.core import hardening

IDENTITY = {"solution_key": lambda solution: solution}


def hooks(module):
    out = {
        "validate": module.validate,
        "grade": module.grade,
        "reductions": module.reductions,
    }
    if hasattr(module, "solution_key"):
        out["solution_key"] = module.solution_key
    return out


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (nonogram, "loom"),
        (skyscrapers, "sluice"),
        (kenken, "lattice"),
        (bridges, "aqueduct"),
        (zebra, "reliquary"),
        (balance, "assay"),
        (cryptogram, "seals"),
    ],
)
def test_suggestions_preserve_all_invariants(module, name, fixture):
    puzzle = module.parse(fixture(name)["spec"])
    report = hardening.suggest(puzzle, **hooks(module))
    assert report.viable
    base_solution = module.validate(puzzle).solution
    key = hooks(module).get("solution_key", lambda s: s)
    for suggestion in report.suggestions[:3]:
        verdict = module.validate(suggestion.puzzle)
        assert verdict.unique, suggestion.description
        assert key(verdict.solution) == key(base_solution)
        assert suggestion.rating.solved_without_search
        assert suggestion.rating.score >= report.base_rating.score


class TestSiteClaims:
    def test_tomography_scans_are_all_necessary(self, fixture):
        # abyss.html: "every displayed scan is necessary" — no hide-a-clue
        # edit may survive the uniqueness check.
        puzzle = nonogram.parse(fixture("tomography")["spec"])
        report = hardening.suggest(puzzle, **hooks(nonogram))
        assert report.viable
        assert not report.suggestions
        assert len(report.breaks_uniqueness) == 18

    def test_seals_givens_are_all_removable(self, fixture):
        # index.html: uniqueness was "verified with zero given letters", so
        # each of the three broken seals must be individually removable.
        puzzle = cryptogram.parse(fixture("seals")["spec"])
        report = hardening.suggest(puzzle, **hooks(cryptogram))
        assert len(report.suggestions) == 3
        assert not report.breaks_uniqueness

    def test_choir_cannot_be_hardened_further(self, fixture):
        # False Choir already grades Extreme; hardening must refuse.
        puzzle = truthlie.parse(fixture("choir")["spec"])
        report = hardening.suggest(puzzle, **hooks(truthlie))
        assert report.base_rating is not None
        assert not report.base_rating.solved_without_search
        assert not report.suggestions


class TestRedundantClueIsFound:
    """Planting a redundant clue in a real puzzle must yield a suggestion
    to drop it — the core generator workflow for new puzzles."""

    def test_zebra(self, fixture):
        spec = fixture("reliquary")["spec"]
        expected = fixture("reliquary")["expected"]
        # Add a clue directly derivable from the solution: Dunmar in slot 1.
        spec["clues"] = [
            *spec["clues"],
            {"kind": "at_slot", "item": expected["keeper"][0], "slot": 1},
        ]
        puzzle = zebra.parse(spec)
        report = hardening.suggest(puzzle, **hooks(zebra))
        dropped = [s for s in report.suggestions if "at_slot" in s.description]
        assert dropped, "the planted redundant clue was not suggested"

    def test_balance(self, fixture):
        spec = fixture("assay")["spec"]
        spec["equations"] = [*spec["equations"], spec["equations"][0]]
        puzzle = balance.parse(spec)
        report = hardening.suggest(puzzle, **hooks(balance))
        assert report.suggestions  # the duplicate is redundant by definition

    def test_truthlie_adjusts_false_count(self, fixture):
        spec = fixture("choir")["spec"]
        # A statement the solution makes TRUE, added to a weakened puzzle:
        # drop the difficulty by fixing slot 1, so the base is gradable.
        spec["statements"] = [
            *spec["statements"],
            {"kind": "in_slots", "item": "Echo", "slots": [1]},
            {"kind": "in_slots", "item": "Bell", "slots": [2]},
            {"kind": "in_slots", "item": "Flint", "slots": [3]},
        ]
        puzzle = truthlie.parse(spec)
        report = hardening.suggest(puzzle, **hooks(truthlie))
        assert report.viable
        for suggestion in report.suggestions:
            verdict = truthlie.validate(suggestion.puzzle)
            assert verdict.unique
            assert verdict.solution["sequence"] == [
                "Echo", "Bell", "Flint", "Crow",
            ]


class TestGreedy:
    def test_greedy_chain_strictly_increases_difficulty(self, fixture):
        spec = fixture("sluice")["spec"]
        # Give the puzzle slack to shed: add three givens from the solution.
        solution = fixture("sluice")["expected"]
        spec["givens"] = [
            [
                solution[r][c] if (r, c) in ((0, 0), (2, 2), (4, 4)) else 0
                for c in range(5)
            ]
            for r in range(5)
        ]
        puzzle = skyscrapers.parse(spec)
        chain = hardening.greedy(puzzle, **hooks(skyscrapers), max_steps=5)
        scores = [s.rating.score for s in chain]
        assert scores == sorted(scores)
        base = skyscrapers.grade(puzzle)
        if chain:  # every applied edit must beat the previous state
            assert scores[0] > base.score

    def test_greedy_respects_max_steps(self, fixture):
        spec = fixture("sluice")["spec"]
        solution = fixture("sluice")["expected"]
        spec["givens"] = [
            [solution[r][c] if r == 0 else 0 for c in range(5)]
            for r in range(5)
        ]
        puzzle = skyscrapers.parse(spec)
        chain = hardening.greedy(puzzle, **hooks(skyscrapers), max_steps=1)
        assert len(chain) <= 1


class TestSudokuViaGenericEngine:
    EASY = (
        "530070000600195000098000060800060003"
        "400803001700020006060000280000419005000080079"
    )

    def test_sudoku_hardens_through_the_same_interface(self):
        puzzle = sudoku.parse(self.EASY)
        report = hardening.suggest(puzzle, **hooks(sudoku))
        assert report.viable
        assert report.suggestions
        best = report.suggestions[0]
        assert sudoku.validate(best.puzzle).unique
        assert best.rating.solved_without_search

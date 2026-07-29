"""Tests for the propagation engine and per-type difficulty grading.

Where the site's pages make claims about their puzzles' solvability, the
grading engine is held to them — most notably Blind Tomography, whose
published solution notes say a line-consistency solver finishes in ten
propagation rounds with no branching.
"""

import pytest

from puzzle_analyzer import (
    balance,
    bridges,
    cryptogram,
    kakuro,
    kenken,
    nonogram,
    skyscrapers,
    starbattle,
    sudoku,
    truthlie,
    wordladder,
    zebra,
)
from puzzle_analyzer.core import EXTREME, Csp, TablePropagator
from puzzle_analyzer.core.csp import (
    AllDifferentPropagator,
    RegularPropagator,
    solve,
)
from puzzle_analyzer.core.grading import grade_csp


class TestEngine:
    def test_propagation_assigns_forced_values(self):
        csp = Csp(
            domains={"x": {1, 2}, "y": {1, 2}},
            propagators=[
                TablePropagator("x is 1", ["x"], [(1,)]),
                AllDifferentPropagator("xy differ", ["x", "y"]),
            ],
        )
        report = solve(csp)
        assert report.solved
        assert report.assignment == {"x": 1, "y": 2}
        assert report.probe_count == 0

    def test_probing_cracks_what_propagation_cannot(self):
        # x+y+z odd-one-out puzzle: no single constraint forces anything,
        # but hypothesising any value propagates to a contradiction or not.
        csp = Csp(
            domains={"x": {1, 2}, "y": {1, 2}, "z": {1, 2}},
            propagators=[
                TablePropagator("x<=y", ["x", "y"], [(1, 1), (1, 2), (2, 2)]),
                TablePropagator("y<=z", ["y", "z"], [(1, 1), (1, 2), (2, 2)]),
                TablePropagator("z<x is false, z<=x", ["z", "x"],
                                [(1, 1), (1, 2), (2, 2)]),
                TablePropagator("x=1", ["x"], [(1,)]),
                TablePropagator("z=1 or z=2 with y", ["z", "y"], [(1, 1)]),
            ],
        )
        report = solve(csp)
        assert report.solved

    def test_stall_reported_when_search_is_needed(self):
        # Two symmetric solutions: nothing to propagate, nothing to refute.
        csp = Csp(
            domains={"x": {1, 2}, "y": {1, 2}},
            propagators=[
                TablePropagator("x != y", ["x", "y"], [(1, 2), (2, 1)])
            ],
        )
        report = solve(csp)
        assert not report.solved and report.stalled

    def test_contradiction_reported(self):
        csp = Csp(
            domains={"x": {1}},
            propagators=[TablePropagator("x = 2", ["x"], [(2,)])],
        )
        report = solve(csp)
        assert report.contradiction

    def test_regular_propagator_prunes_like_the_clue(self):
        # Clue [2] on a 3-cell line: 110, 011 -> middle cell always 1.
        from puzzle_analyzer.nonogram import _automaton

        triples, final = _automaton((2,))
        transitions = {(s, sym): n for s, sym, n in triples}
        prop = RegularPropagator("[2]", ["a", "b", "c"], transitions, 0, [final])
        domains = {"a": {0, 1}, "b": {0, 1}, "c": {0, 1}}
        eliminations = prop.prune(domains)
        assert ("b", 0) in eliminations

    def test_grade_maps_stall_to_extreme(self):
        csp = Csp(
            domains={"x": {1, 2}, "y": {1, 2}},
            propagators=[
                TablePropagator("x != y", ["x", "y"], [(1, 2), (2, 1)])
            ],
        )
        rating = grade_csp(csp)
        assert rating.grade == EXTREME
        assert not rating.solved_without_search
        assert rating.score >= 1000


class TestSiteClaims:
    """Grades must be consistent with what the pages say about their puzzles."""

    def test_tomography_solves_in_ten_rounds_with_no_branching(self, fixture):
        # abyss.html: "A line-consistency solver completes all 100 cells in
        # ten propagation rounds with no branching."
        rating = nonogram.grade(nonogram.parse(fixture("tomography")["spec"]))
        assert rating.solved_without_search
        assert rating.detail["probeEliminations"] == 0
        assert rating.detail["waves"] == 10

    def test_lattice_needs_no_guesses(self, fixture):
        # abyss.html: "cage restrictions and Latin-square elimination are
        # sufficient" — pure propagation must finish it.
        rating = kenken.grade(kenken.parse(fixture("lattice")["spec"]))
        assert rating.solved_without_search
        assert rating.detail["probeEliminations"] == 0

    def test_choir_grades_extreme(self, fixture):
        # abyss.html describes solving False Choir by hypothesising lie
        # sets and discarding contradictory branches — that is search.
        rating = truthlie.grade(truthlie.parse(fixture("choir")["spec"]))
        assert rating.grade == EXTREME


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (nonogram, "loom"),
        (skyscrapers, "sluice"),
        (kakuro, "apothecary"),
        (starbattle, "aviary"),
        (bridges, "aqueduct"),
        (zebra, "reliquary"),
        (zebra, "switchyard"),
        (balance, "assay"),
        (cryptogram, "seals"),
        (cryptogram, "cipher"),
        (wordladder, "stair"),
    ],
)
def test_site_puzzles_grade_without_search(module, name, fixture):
    """Every non-Extreme site puzzle must be gradable without guessing."""
    rating = module.grade(module.parse(fixture(name)["spec"]))
    assert rating.solved_without_search, rating
    assert rating.grade in ("Easy", "Medium", "Hard", "Very Hard")
    assert rating.steps  # annotated deductions are always produced


class TestSudokuAdapter:
    EASY = (
        "530070000600195000098000060800060003"
        "400803001700020006060000280000419005000080079"
    )

    def test_grade_wraps_technique_solver(self):
        rating = sudoku.grade(sudoku.parse(self.EASY))
        assert rating.grade == "Easy"
        assert rating.solved_without_search
        assert rating.detail["hardestTechnique"] == "Naked Single"
        assert any("Naked Single" in step for step in rating.steps)

    def test_invalid_puzzle_grades_invalid(self):
        rating = sudoku.grade(sudoku.parse("55" + self.EASY[2:]))
        assert rating.grade == "Invalid"
        assert not rating.solved_without_search

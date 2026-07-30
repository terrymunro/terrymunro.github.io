"""Tests for the CP-SAT grid puzzle modules.

Positive cases are the actual puzzles published on the site, asserted
against their published solutions; negative cases corrupt or under-clue
each puzzle to prove the validator notices.
"""

import pytest

from puzzle_analyzer import (
    bridges,
    kakuro,
    kenken,
    nonogram,
    skyscrapers,
    starbattle,
)
from puzzle_analyzer.core.spec import SpecError


class TestNonogram:
    def test_loom_matches_published_solution(self, fixture):
        data = fixture("loom")
        verdict = nonogram.validate(nonogram.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_tomography_unique_despite_destroyed_scans(self, fixture):
        data = fixture("tomography")
        spec = data["spec"]
        assert None in spec["cols"]  # two dead column scanners
        verdict = nonogram.validate(nonogram.parse(spec))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_removing_a_third_scan_breaks_uniqueness(self, fixture):
        spec = fixture("tomography")["spec"]
        # The page claims all 18 surviving scans are necessary; check one.
        spec["rows"][0] = None
        verdict = nonogram.validate(nonogram.parse(spec))
        assert verdict.solution_count >= 2

    def test_impossible_clue_is_malformed(self):
        verdict = nonogram.validate(
            nonogram.parse({"rows": [[3, 3]], "cols": [[1], [1], [1], [1], [1]]})
        )
        assert not verdict.well_formed
        assert "cannot fit" in verdict.issues[0]

    def test_inconsistent_totals_reported(self):
        verdict = nonogram.validate(
            nonogram.parse({"rows": [[2], [0]], "cols": [[1], [0]]})
        )
        assert not verdict.well_formed


class TestSkyscrapers:
    def test_sluice_matches_published_solution(self, fixture):
        data = fixture("sluice")
        verdict = skyscrapers.validate(skyscrapers.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_dropping_a_clue_breaks_uniqueness(self, fixture):
        spec = fixture("sluice")["spec"]
        spec["top"] = [0, 0, 0, 2, 0]
        verdict = skyscrapers.validate(skyscrapers.parse(spec))
        assert verdict.solution_count >= 2

    def test_contradictory_clues_have_no_solution(self, fixture):
        spec = fixture("sluice")["spec"]
        spec["top"][0] = 5  # would need ascending 1..5 in that column
        spec["bottom"][0] = 5  # ...and descending — impossible together
        verdict = skyscrapers.validate(skyscrapers.parse(spec))
        assert verdict.well_formed and verdict.solution_count == 0

    def test_out_of_range_clue_is_malformed(self):
        verdict = skyscrapers.validate(
            skyscrapers.parse({"size": 4, "top": [9, 0, 0, 0]})
        )
        assert not verdict.well_formed


class TestKenKen:
    def test_lattice_matches_published_solution(self, fixture):
        data = fixture("lattice")
        verdict = kenken.validate(kenken.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_label_parsing_covers_unicode_operators(self):
        assert kenken.parse_label("30×") == ("*", 30)
        assert kenken.parse_label("5÷") == ("/", 5)
        assert kenken.parse_label("2−") == ("-", 2)
        assert kenken.parse_label("7+") == ("+", 7)
        with pytest.raises(SpecError):
            kenken.parse_label("nope")

    def test_incomplete_cage_cover_is_malformed(self, fixture):
        spec = fixture("lattice")["spec"]
        spec["cages"] = spec["cages"][:-1]
        verdict = kenken.validate(kenken.parse(spec))
        assert not verdict.well_formed
        assert "do not cover" in verdict.issues[0]

    def test_overlapping_cages_are_malformed(self, fixture):
        spec = fixture("lattice")["spec"]
        spec["cages"][1]["cells"][0] = [0, 0]  # also in cage 1
        verdict = kenken.validate(kenken.parse(spec))
        assert not verdict.well_formed

    def test_relaxed_cage_breaks_uniqueness(self, fixture):
        spec = fixture("lattice")["spec"]
        # Merge the two-cell 2x cage and the 9+ cage into one big additive
        # cage: weaker information, multiple grids fit.
        cages = spec["cages"]
        merged = {
            "cells": cages[0]["cells"] + cages[4]["cells"],
            "op": "+",
            "target": 12,
        }
        spec["cages"] = [merged, *cages[1:4], *cages[5:]]
        verdict = kenken.validate(kenken.parse(spec))
        assert verdict.solution_count >= 2


class TestKakuro:
    def test_apothecary_matches_published_solution(self, fixture):
        data = fixture("apothecary")
        verdict = kakuro.validate(kakuro.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_wrong_sum_has_no_solution(self, fixture):
        spec = fixture("apothecary")["spec"]
        spec["runs"][0]["sum"] = 4  # published run needs 11
        verdict = kakuro.validate(kakuro.parse(spec))
        assert verdict.well_formed and verdict.solution_count == 0

    def test_infeasible_sum_is_malformed(self, fixture):
        spec = fixture("apothecary")["spec"]
        spec["runs"][0]["sum"] = 18  # two distinct digits max out at 17
        verdict = kakuro.validate(kakuro.parse(spec))
        assert not verdict.well_formed

    def test_nine_cell_run_grades_without_error(self):
        # Codex review finding (PR #5): a full-length run used to build a
        # 9! permutation table and blow the table-size cap during grading.
        spec = {
            "layout": [[1] * 9],
            "runs": [{"dir": "h", "anchor": [0, 0], "len": 9, "sum": 45}],
        }
        puzzle = kakuro.parse(spec)
        rating = kakuro.grade(puzzle)  # must not raise
        assert rating.grade  # a lone 9-run is wildly ambiguous; any grade is fine
        assert kakuro.validate(puzzle).solution_count >= 2

    def test_nine_cell_run_with_wrong_sum_grades_invalid(self):
        # Codex review finding (PR #7): the 9-run shortcut must not drop
        # the sum constraint when grading skips check().
        spec = {
            "layout": [[1] * 9],
            "runs": [{"dir": "h", "anchor": [0, 0], "len": 9, "sum": 44}],
        }
        rating = kakuro.grade(kakuro.parse(spec))
        assert not rating.solved_without_search
        assert "contradiction" in rating.detail

    def test_run_over_blocked_cell_is_malformed(self, fixture):
        spec = fixture("apothecary")["spec"]
        spec["runs"][0]["len"] = 5  # walks off the white run
        verdict = kakuro.validate(kakuro.parse(spec))
        assert not verdict.well_formed


class TestStarBattle:
    def test_aviary_matches_published_solution(self, fixture):
        data = fixture("aviary")
        verdict = starbattle.validate(starbattle.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_solution_stars_never_touch(self, fixture):
        verdict = starbattle.validate(
            starbattle.parse(fixture("aviary")["spec"])
        )
        stars = [
            (r, cols[0]) for r, cols in enumerate(verdict.solution)
        ]
        for i, (r1, c1) in enumerate(stars):
            for r2, c2 in stars[i + 1 :]:
                assert max(abs(r1 - r2), abs(c1 - c2)) > 1

    def test_wrong_region_count_is_malformed(self):
        verdict = starbattle.validate(
            starbattle.parse({"regions": [[0, 0], [0, 0]], "stars": 1})
        )
        assert not verdict.well_formed


class TestBridges:
    def test_aqueduct_matches_published_solution(self, fixture):
        data = fixture("aqueduct")
        verdict = bridges.validate(bridges.parse(data["spec"]))
        assert verdict.unique
        built = sorted(
            [min(e["a"], e["b"]), max(e["a"], e["b"]), e["bridges"]]
            for e in verdict.solution
        )
        assert built == data["expected"]

    def test_connectivity_is_enforced(self):
        # Two disjoint pairs satisfy all degree constraints but form two
        # networks; the validator must reject the configuration.
        spec = {
            "islands": [
                {"r": 0, "c": 0, "deg": 1},
                {"r": 0, "c": 2, "deg": 1},
                {"r": 2, "c": 0, "deg": 1},
                {"r": 2, "c": 2, "deg": 1},
            ]
        }
        verdict = bridges.validate(bridges.parse(spec))
        assert verdict.well_formed and verdict.solution_count == 0

    def test_odd_degree_sum_is_malformed(self):
        verdict = bridges.validate(
            bridges.parse(
                {"islands": [{"r": 0, "c": 0, "deg": 1}, {"r": 0, "c": 2, "deg": 2}]}
            )
        )
        assert not verdict.well_formed

    def test_crossing_bridges_are_forbidden(self):
        # A plus-shaped layout where satisfying all degrees requires the
        # horizontal and vertical bridges to cross.
        spec = {
            "islands": [
                {"r": 1, "c": 0, "deg": 1},
                {"r": 1, "c": 2, "deg": 1},
                {"r": 0, "c": 1, "deg": 1},
                {"r": 2, "c": 1, "deg": 1},
            ]
        }
        verdict = bridges.validate(bridges.parse(spec))
        assert verdict.solution_count == 0

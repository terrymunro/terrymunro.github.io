"""Tests for the shared core: verdicts, CP-SAT enumeration, wordlists."""

import pytest

from puzzle_analyzer.core import (
    CpModelBuilder,
    Verdict,
    enumerate_solutions,
    load_wordlist,
)
from puzzle_analyzer.core.spec import SpecError, get_field


class TestVerdict:
    def test_unique_requires_wellformed_and_one_solution(self):
        good = Verdict("t", well_formed=True, solution_count=1, solutions=["s"])
        assert good.unique and good.solution == "s"
        assert not Verdict("t", well_formed=True, solution_count=2).unique
        assert not Verdict("t", well_formed=False, solution_count=1).unique

    def test_to_dict_caps_solution_count(self):
        verdict = Verdict("t", well_formed=True, solution_count=2)
        assert verdict.to_dict()["solutionCount"] == "2+"

    def test_malformed_helper(self):
        verdict = Verdict.malformed("t", ["bad"])
        assert not verdict.well_formed and verdict.issues == ["bad"]


class TestEnumeration:
    def _two_var_model(self):
        builder = CpModelBuilder()
        x = builder.model.new_int_var(1, 3, "x")
        y = builder.model.new_int_var(1, 3, "y")
        builder.model.add(x + y == 4)  # (1,3), (2,2), (3,1)
        return builder, x, y

    def test_enumerates_all_solutions_up_to_limit(self):
        builder, x, y = self._two_var_model()
        found = enumerate_solutions(
            builder.model, [x, y], limit=10, decode=tuple
        )
        assert sorted(found) == [(1, 3), (2, 2), (3, 1)]

    def test_limit_stops_early(self):
        builder, x, y = self._two_var_model()
        found = enumerate_solutions(builder.model, [x, y], limit=2, decode=tuple)
        assert len(found) == 2

    def test_auxiliary_variables_do_not_duplicate_solutions(self):
        builder, x, y = self._two_var_model()
        free = builder.model.new_int_var(0, 5, "free")  # noqa: F841
        found = enumerate_solutions(
            builder.model, [x, y], limit=20, decode=tuple
        )
        assert sorted(found) == [(1, 3), (2, 2), (3, 1)]

    def test_accept_filters_solutions(self):
        builder, x, y = self._two_var_model()
        found = enumerate_solutions(
            builder.model,
            [x, y],
            limit=10,
            decode=tuple,
            accept=lambda vals: vals[0] != vals[1],
        )
        assert sorted(found) == [(1, 3), (3, 1)]

    def test_latin_square_helper(self):
        builder = CpModelBuilder()
        grid = builder.int_grid(2, 2, 1, 2)
        builder.latin_square(grid)
        found = enumerate_solutions(
            builder.model,
            [grid[r][c] for r in range(2) for c in range(2)],
            limit=10,
            decode=tuple,
        )
        assert sorted(found) == [(1, 2, 2, 1), (2, 1, 1, 2)]


class TestSpec:
    def test_missing_required_field(self):
        with pytest.raises(SpecError, match="missing required field"):
            get_field({}, "size", int)

    def test_wrong_type(self):
        with pytest.raises(SpecError, match="must be int"):
            get_field({"size": "big"}, "size", int)

    def test_optional_default(self):
        assert get_field({}, "stars", int, 1, required=False) == 1


class TestWordlist:
    def test_uppercases_and_skips_comments(self):
        words = load_wordlist(["maze", "# comment", "", "Mace"])
        assert words == {"MAZE", "MACE"}

    def test_loads_from_file(self, tmp_path):
        path = tmp_path / "words.txt"
        path.write_text("cold\ncord\n", encoding="utf-8")
        assert load_wordlist(str(path)) == {"COLD", "CORD"}

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            load_wordlist([])

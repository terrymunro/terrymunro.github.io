"""CLI and registry tests."""

import json

import pytest

from puzzle_analyzer import PUZZLE_TYPES, get_puzzle_type
from puzzle_analyzer.cli import main

EASY_SUDOKU = (
    "530070000600195000098000060800060003"
    "400803001700020006060000280000419005000080079"
)


class TestRegistry:
    def test_all_types_expose_parse_and_validate(self):
        for puzzle_type in PUZZLE_TYPES.values():
            assert callable(puzzle_type.parse)
            assert callable(puzzle_type.validate)

    def test_every_page_puzzle_type_is_registered(self):
        expected = {
            "sudoku",
            "nonogram",
            "skyscrapers",
            "kenken",
            "kakuro",
            "starbattle",
            "bridges",
            "zebra",
            "truthlie",
            "cryptogram",
            "wordladder",
            "balance",
        }
        assert set(PUZZLE_TYPES) == expected

    def test_unknown_type_raises_with_known_list(self):
        with pytest.raises(ValueError, match="unknown puzzle type"):
            get_puzzle_type("crossword")


class TestCli:
    def test_types_lists_everything(self, capsys):
        assert main(["types"]) == 0
        out = capsys.readouterr().out
        for name in PUZZLE_TYPES:
            assert name in out

    def test_validate_json_spec_from_file(self, fixture, tmp_path, capsys):
        spec_path = tmp_path / "sluice.json"
        spec_path.write_text(json.dumps(fixture("sluice")["spec"]))
        assert main(["validate", "skyscrapers", str(spec_path), "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["unique"] is True
        assert report["solution"] == fixture("sluice")["expected"]

    def test_validate_inline_json(self, fixture, capsys):
        spec = json.dumps(fixture("assay")["spec"])
        assert main(["validate", "balance", spec]) == 0
        assert "exactly one solution" in capsys.readouterr().out

    def test_validate_sudoku_raw_string(self, capsys):
        assert main(["validate", "sudoku", EASY_SUDOKU, "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["unique"] is True
        assert report["grade"] == "Easy"

    def test_validate_rejects_unknown_type(self, capsys):
        assert main(["validate", "crossword", "{}"]) == 2
        assert "unknown puzzle type" in capsys.readouterr().err

    def test_validate_reports_malformed_spec(self, capsys):
        assert main(["validate", "kenken", '{"size": 2, "cages": []}']) == 1
        assert "malformed" in capsys.readouterr().out

    def test_sudoku_subcommand_still_works(self, capsys):
        assert main(["sudoku", "validate", EASY_SUDOKU]) == 0
        out = capsys.readouterr().out
        assert "unique solution: yes" in out
        assert "difficulty: Easy" in out

    def test_sudoku_min_grade_gate(self, capsys):
        assert main(["sudoku", "validate", EASY_SUDOKU, "--min-grade", "Hard"]) == 1

    def test_sudoku_solve_annotates_steps(self, capsys):
        assert main(["sudoku", "solve", EASY_SUDOKU, "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["steps"]
        assert all(
            step["technique"] and step["description"] for step in report["steps"]
        )

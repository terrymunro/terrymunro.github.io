"""End-to-end and soundness tests for the sudoku module."""

import itertools

import pytest

from puzzle_analyzer.sudoku import (
    analyze,
    count_solutions,
    greedy_harden,
    is_unique,
    parse_puzzle,
    solve_logically,
    suggest_removals,
    to_line,
)
from puzzle_analyzer.sudoku.grid import find_given_conflicts

# Classic easy puzzle (Wikipedia); solvable with singles alone.
EASY = (
    "530070000600195000098000060800060003"
    "400803001700020006060000280000419005000080079"
)
# Inkala "Everest" — unique but needs chains, beyond the repertoire.
EXTREME = (
    "800000000003600000070090200050007000"
    "000045700000100030001000068008500010090000400"
)
# EASY hardened by the greedy hardener; requires XY-Wing.
HARDENED = (
    "53..........1.5....98....6.....6...3"
    "4..8.3..17...2.....6....28....4....5....8..7."
)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def test_parse_roundtrip():
    values = parse_puzzle(EASY)
    assert len(values) == 81
    assert to_line(values).replace(".", "0") == EASY


def test_parse_accepts_pretty_grids():
    pretty = "5 3 . | . 7 .\n" + EASY[6:]
    assert parse_puzzle(pretty) == parse_puzzle(EASY)


def test_parse_rejects_bad_input():
    with pytest.raises(ValueError):
        parse_puzzle(EASY[:-1])
    with pytest.raises(ValueError):
        parse_puzzle(EASY[:-1] + "q")


def test_conflicting_givens_detected():
    bad = "55" + EASY[2:]
    assert find_given_conflicts(parse_puzzle(bad))


# --------------------------------------------------------------------------
# Uniqueness (OR-Tools)
# --------------------------------------------------------------------------

def test_easy_puzzle_is_unique():
    assert is_unique(parse_puzzle(EASY))


def test_empty_grid_has_multiple_solutions():
    assert len(count_solutions([0] * 81, limit=2)) == 2


def test_unsolvable_puzzle_has_no_solutions():
    # Force a contradiction: row 1 leaves only 3 for R1C3, but column 3
    # already contains a 3.
    values = parse_puzzle(
        "12.456789"
        "..3......"
        "........."
        "........."
        "........."
        "........."
        "........."
        "........."
        "........."
    )
    assert count_solutions(values, limit=2) == []


# --------------------------------------------------------------------------
# Logical solver
# --------------------------------------------------------------------------

def test_easy_puzzle_solved_by_singles_and_matches_cp_sat():
    analysis = analyze(parse_puzzle(EASY))
    assert analysis.valid
    assert analysis.solvable_without_guessing
    assert analysis.rating.grade == "Easy"
    assert analysis.solve.final_values == analysis.solution


def test_extreme_puzzle_stalls_without_guessing():
    analysis = analyze(parse_puzzle(EXTREME))
    assert analysis.valid  # unique...
    assert not analysis.solvable_without_guessing  # ...but needs chains
    assert "Extreme" in analysis.rating.grade


def test_hardened_puzzle_uses_intermediate_techniques():
    analysis = analyze(parse_puzzle(HARDENED))
    assert analysis.valid
    assert analysis.solvable_without_guessing
    counts = analysis.solve.technique_counts
    assert "Locked Candidates (Pointing)" in counts
    assert analysis.rating.grade in ("Hard", "Very Hard")


def test_every_step_is_sound():
    """No step may eliminate the true solution digit or place a wrong one."""
    analysis = analyze(parse_puzzle(HARDENED))
    solution = analysis.solution
    for step in analysis.solve.steps:
        for cell, digit in step.placements:
            assert solution[cell] == digit, (
                f"{step.technique} placed {digit} but solution has "
                f"{solution[cell]}: {step.description}"
            )
        for cell, digit in step.eliminations:
            assert solution[cell] != digit, (
                f"{step.technique} eliminated the solution digit {digit}: "
                f"{step.description}"
            )


def test_solver_never_guesses_on_invalid_input():
    result = solve_logically([0] * 81)
    assert not result.solved  # stalls immediately, no progress possible
    assert result.contradiction is None


# --------------------------------------------------------------------------
# Hardening
# --------------------------------------------------------------------------

def test_suggestions_preserve_uniqueness_and_solvability():
    report = suggest_removals(parse_puzzle(EASY))
    assert report.suggestions, "easy puzzle should have hardening headroom"
    for s in report.suggestions[:3]:
        sub = analyze(s.new_puzzle)
        assert sub.valid
        assert sub.solvable_without_guessing
        assert sub.solution == analyze(parse_puzzle(EASY)).solution
        assert s.rating.score >= report.base.rating.score


def test_greedy_harden_strictly_increases_difficulty():
    chain = greedy_harden(parse_puzzle(EASY), max_removals=3)
    assert chain
    base_score = analyze(parse_puzzle(EASY)).rating.score
    scores = [s.rating.score for s in chain]
    assert scores[0] > base_score
    assert all(b > a for a, b in itertools.pairwise(scores))

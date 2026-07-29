"""The `sudoku` CLI subcommand: validate, solve, rate and harden.

Sudoku gets a richer command surface than the generic `validate` because
it has the annotated no-guessing solver and the hardener on top of the
uniqueness check.
"""

import argparse
import json
import sys
from pathlib import Path

from .analyze import Analysis, analyze
from .grid import cell_name, format_grid, parse_puzzle, to_line
from .harden import greedy_harden, suggest_removals

GRADES = ["Easy", "Medium", "Hard", "Very Hard"]


def _load_puzzle(arg: str) -> list[int]:
    if arg == "-":
        return parse_puzzle(sys.stdin.read())
    if Path(arg).exists():
        return parse_puzzle(Path(arg).read_text(encoding="utf-8"))
    return parse_puzzle(arg)


def _analysis_dict(analysis: Analysis) -> dict:
    out: dict = {
        "puzzle": to_line(analysis.values),
        "wellFormed": not analysis.conflicts,
        "conflicts": analysis.conflicts,
        "solutionCount": (
            "2+" if analysis.solution_count >= 2 else analysis.solution_count
        ),
        "unique": analysis.valid,
        "solvableWithoutGuessing": analysis.solvable_without_guessing,
    }
    if analysis.rating and analysis.solve:
        out["grade"] = analysis.rating.grade
        out["hardestTechnique"] = analysis.rating.hardest_technique
        out["score"] = analysis.rating.score
        out["techniqueCounts"] = analysis.solve.technique_counts
    return out


def _print_validity(analysis: Analysis) -> None:
    if analysis.conflicts:
        print("INVALID: conflicting givens")
        for conflict in analysis.conflicts:
            print(f"  - {conflict}")
        return
    if analysis.solution_count == 0:
        print("INVALID: no solution exists")
        return
    if analysis.solution_count >= 2:
        print("INVALID: multiple solutions exist (not a proper puzzle)")
        return
    print("unique solution: yes (proved with OR-Tools CP-SAT)")
    if analysis.solvable_without_guessing:
        print("solvable without guessing: yes")
    else:
        print(
            "solvable without guessing: NO — needs techniques beyond the "
            "repertoire (chains or trial-and-error)"
        )
    assert analysis.rating and analysis.solve
    print(f"difficulty: {analysis.rating.grade}")
    print(f"hardest technique: {analysis.rating.hardest_technique}")
    print(f"score: {analysis.rating.score}")
    if counts := analysis.solve.technique_counts:
        print("techniques used:")
        for name, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {count:3d} x {name}")


def cmd_validate(args: argparse.Namespace) -> int:
    analysis = analyze(_load_puzzle(args.puzzle))
    if args.json:
        print(json.dumps(_analysis_dict(analysis), indent=2))
    else:
        _print_validity(analysis)

    ok = analysis.valid and analysis.solvable_without_guessing
    if ok and args.min_grade:
        assert analysis.rating
        if GRADES.index(analysis.rating.grade) < GRADES.index(args.min_grade):
            if not args.json:
                print(
                    f"FAIL: grade {analysis.rating.grade} is below the "
                    f"required minimum ({args.min_grade})"
                )
            ok = False
    return 0 if ok else 1


def cmd_solve(args: argparse.Namespace) -> int:
    values = _load_puzzle(args.puzzle)
    analysis = analyze(values)

    if args.json:
        out = _analysis_dict(analysis)
        if analysis.solve:
            out["steps"] = [
                {
                    "technique": s.technique,
                    "description": s.description,
                    "placements": [
                        {"cell": cell_name(c), "digit": d}
                        for c, d in s.placements
                    ],
                    "eliminations": [
                        {"cell": cell_name(c), "digit": d}
                        for c, d in s.eliminations
                    ],
                }
                for s in analysis.solve.steps
            ]
            out["finalGrid"] = to_line(analysis.solve.final_values)
        print(json.dumps(out, indent=2))
        return 0 if analysis.solvable_without_guessing else 1

    print(format_grid(values))
    print()
    _print_validity(analysis)
    if not analysis.solve:
        return 1
    print()
    for i, step in enumerate(analysis.solve.steps, 1):
        print(f"{i:3d}. [{step.technique}] {step.description}")
    print()
    if analysis.solve.solved:
        print("solved by pure logic:")
        print(format_grid(analysis.solve.final_values))
        return 0
    print("stalled here (further progress needs chains or guessing):")
    print(format_grid(analysis.solve.final_values))
    return 1


def cmd_rate(args: argparse.Namespace) -> int:
    analysis = analyze(_load_puzzle(args.puzzle))
    if args.json:
        print(json.dumps(_analysis_dict(analysis), indent=2))
    else:
        _print_validity(analysis)
    return 0 if analysis.valid else 1


def _suggestion_dict(s) -> dict:
    return {
        "cell": cell_name(s.cell),
        "digit": s.digit,
        "grade": s.rating.grade,
        "hardestTechnique": s.rating.hardest_technique,
        "score": s.rating.score,
        "puzzle": to_line(s.new_puzzle),
    }


def cmd_harden(args: argparse.Namespace) -> int:
    values = _load_puzzle(args.puzzle)

    if args.greedy:
        chain = greedy_harden(values, max_removals=args.max_removals)
        if not chain:
            print("no removal makes this puzzle strictly harder")
            return 1
        if args.json:
            print(
                json.dumps(
                    {
                        "removals": [_suggestion_dict(s) for s in chain],
                        "hardenedPuzzle": to_line(chain[-1].new_puzzle),
                    },
                    indent=2,
                )
            )
            return 0
        print(f"applied {len(chain)} removal(s):")
        for s in chain:
            print(f"  - {s.describe()}")
        print()
        print("hardened puzzle (same solution, no guessing needed):")
        print(format_grid(chain[-1].new_puzzle))
        print()
        print(to_line(chain[-1].new_puzzle))
        return 0

    report = suggest_removals(values)
    if not report.base.valid:
        print("puzzle is not valid (see `validate`); cannot harden")
        return 1
    if not report.base.solvable_without_guessing:
        print("puzzle already requires guessing; cannot harden further")
        return 1

    limit = args.max_suggestions
    if args.json:
        print(
            json.dumps(
                {
                    "base": _analysis_dict(report.base),
                    "suggestions": [
                        _suggestion_dict(s) for s in report.suggestions[:limit]
                    ],
                    "removalBreaksUniqueness": [
                        cell_name(c) for c in report.breaks_uniqueness
                    ],
                    "removalRequiresGuessing": [
                        cell_name(c) for c in report.breaks_solvability
                    ],
                },
                indent=2,
            )
        )
        return 0

    base = report.base.rating
    assert base
    print(
        f"current difficulty: {base.grade} "
        f"(hardest: {base.hardest_technique}, score {base.score})"
    )
    if not report.suggestions:
        print("no single-given removal keeps the puzzle valid and guess-free")
    else:
        print(f"top {min(limit, len(report.suggestions))} suggestion(s):")
        for s in report.suggestions[:limit]:
            marker = "*" if s.rating.score > base.score else " "
            print(f" {marker} {s.describe()}")
        print("  (* = strictly harder than the current puzzle)")
    if report.breaks_uniqueness:
        names = ", ".join(cell_name(c) for c in report.breaks_uniqueness)
        print(f"cannot remove (solution would no longer be unique): {names}")
    if report.breaks_solvability:
        names = ", ".join(cell_name(c) for c in report.breaks_solvability)
        print(f"cannot remove (puzzle would require guessing): {names}")
    return 0


def register(subparsers) -> None:
    """Attach the `sudoku` command tree to the main parser."""
    parser = subparsers.add_parser(
        "sudoku",
        help="sudoku-specific commands: validate, solve, rate, harden",
    )
    sub = parser.add_subparsers(dest="sudoku_command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "puzzle",
            help="81-char puzzle string, a file path, or - for stdin",
        )
        p.add_argument("--json", action="store_true", help="JSON output")

    p = sub.add_parser(
        "validate",
        help="check uniqueness, guess-free solvability and difficulty",
    )
    add_common(p)
    p.add_argument(
        "--min-grade",
        choices=GRADES,
        help="exit non-zero unless the puzzle is at least this hard",
    )
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("solve", help="show every solving step, annotated")
    add_common(p)
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("rate", help="report the difficulty grade")
    add_common(p)
    p.set_defaults(func=cmd_rate)

    p = sub.add_parser(
        "harden",
        help="suggest given-removals that make the puzzle harder",
    )
    add_common(p)
    p.add_argument(
        "--max-suggestions",
        type=int,
        default=10,
        metavar="N",
        help="show at most N suggestions (default 10)",
    )
    p.add_argument(
        "--greedy",
        action="store_true",
        help="repeatedly apply the best removal and output the result",
    )
    p.add_argument(
        "--max-removals",
        type=int,
        default=None,
        metavar="N",
        help="with --greedy, stop after N removals",
    )
    p.set_defaults(func=cmd_harden)

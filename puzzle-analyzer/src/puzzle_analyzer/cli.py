"""Command-line interface.

Usage examples::

    puzzle-analyzer types
    puzzle-analyzer validate kenken lattice.json
    puzzle-analyzer validate nonogram - < clues.json
    puzzle-analyzer validate sudoku "53..7....6..195...."
    puzzle-analyzer grade zebra reliquary.json
    puzzle-analyzer harden nonogram clues.json --greedy
    puzzle-analyzer sudoku solve PUZZLE
    puzzle-analyzer sudoku harden PUZZLE --greedy

Specs are JSON documents (see each module's docstring for its format),
passed as a file path, ``-`` for stdin, or an inline JSON string.  Sudoku
also accepts its classic 81-character string everywhere.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import hardening
from .core.spec import SpecError
from .registry import PUZZLE_TYPES, PuzzleType, get_puzzle_type
from .sudoku import cli as sudoku_cli


def _is_existing_file(arg: str) -> bool:
    try:
        return Path(arg).is_file()
    except OSError:  # e.g. inline JSON longer than a legal file name
        return False


def _load_spec(arg: str) -> Any:
    if arg == "-":
        text = sys.stdin.read()
    elif _is_existing_file(arg):
        text = Path(arg).read_text(encoding="utf-8")
    else:
        text = arg
    try:
        spec = json.loads(text)
    except json.JSONDecodeError:
        # Not JSON — let the puzzle module decide (sudoku accepts raw grids).
        return text
    # A bare 81-digit sudoku string parses as a huge JSON number; only
    # containers are real specs.
    return spec if isinstance(spec, dict | list) else text


def cmd_types(args: argparse.Namespace) -> int:
    if args.json:
        print(
            json.dumps(
                {
                    name: {
                        "summary": t.summary,
                        "foundIn": t.found_in,
                        "capabilities": t.capabilities,
                    }
                    for name, t in sorted(PUZZLE_TYPES.items())
                },
                indent=2,
            )
        )
        return 0
    width = max(len(name) for name in PUZZLE_TYPES)
    for name, puzzle_type in sorted(PUZZLE_TYPES.items()):
        tags = ",".join(puzzle_type.capabilities)
        print(f"{name:<{width}}  [{tags}] {puzzle_type.summary}")
        if puzzle_type.found_in != "—":
            print(f"{'':<{width}}  found in: {puzzle_type.found_in}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    puzzle_type = get_puzzle_type(args.type)
    puzzle = puzzle_type.parse(_load_spec(args.spec))
    verdict = puzzle_type.validate(puzzle, limit=max(2, args.limit))

    if args.json:
        print(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False))
        return 0 if verdict.unique else 1

    if not verdict.well_formed:
        print(f"INVALID {args.type}: malformed puzzle")
        for issue in verdict.issues:
            print(f"  - {issue}")
        return 1
    match verdict.solution_count:
        case 0:
            print(f"INVALID {args.type}: no solution exists")
            for issue in verdict.issues:
                print(f"  - {issue}")
            return 1
        case 1:
            print(f"VALID {args.type}: exactly one solution (proved)")
            print(json.dumps(verdict.solution, indent=2, ensure_ascii=False))
            for key, value in verdict.details.items():
                print(f"{key}: {value}")
            return 0
        case _:
            print(
                f"INVALID {args.type}: multiple solutions exist "
                f"(not a proper puzzle)"
            )
            return 1


def _harden_hooks(puzzle_type: PuzzleType) -> dict[str, Any]:
    if "harden" not in puzzle_type.capabilities:
        raise ValueError(
            f"puzzle type {puzzle_type.name!r} does not support hardening "
            f"(capabilities: {', '.join(puzzle_type.capabilities)})"
        )
    return {
        "validate": puzzle_type.validate,
        "grade": puzzle_type.grade,
        "reductions": puzzle_type.reductions,
        "solution_key": puzzle_type.solution_key,
    }


def cmd_grade(args: argparse.Namespace) -> int:
    puzzle_type = get_puzzle_type(args.type)
    if puzzle_type.grade is None:
        raise ValueError(f"puzzle type {args.type!r} does not support grading")
    puzzle = puzzle_type.parse(_load_spec(args.spec))
    rating = puzzle_type.grade(puzzle)

    if args.json:
        out = rating.to_dict()
        if args.steps:
            out["steps"] = rating.steps
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"difficulty: {rating.grade}")
        print(f"score: {rating.score}")
        solvable = "yes" if rating.solved_without_search else "NO"
        print(f"solvable without search: {solvable}")
        for key, value in rating.detail.items():
            print(f"{key}: {value}")
        if args.steps:
            for index, step in enumerate(rating.steps, 1):
                print(f"{index:4d}. {step}")
    return 0 if rating.solved_without_search else 1


def cmd_harden(args: argparse.Namespace) -> int:
    puzzle_type = get_puzzle_type(args.type)
    hooks = _harden_hooks(puzzle_type)
    puzzle = puzzle_type.parse(_load_spec(args.spec))

    if args.greedy:
        chain = hardening.greedy(puzzle, **hooks, max_steps=args.max_steps)
        if args.json:
            print(
                json.dumps(
                    {
                        "applied": [
                            {
                                "edit": s.description,
                                "grade": s.rating.grade,
                                "score": s.rating.score,
                            }
                            for s in chain
                        ]
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0 if chain else 1
        if not chain:
            print("no edit makes this puzzle strictly harder")
            return 1
        print(f"applied {len(chain)} edit(s):")
        for suggestion in chain:
            print(f"  - {suggestion.describe()}")
        print()
        print("hardened puzzle (same solution, still no search needed):")
        print(repr(chain[-1].puzzle))
        return 0

    report = hardening.suggest(puzzle, **hooks)
    if args.json:
        print(
            json.dumps(
                {
                    "viable": report.viable,
                    "base": (
                        report.base_rating.to_dict() if report.base_rating else None
                    ),
                    "suggestions": [
                        {
                            "edit": s.description,
                            "grade": s.rating.grade,
                            "score": s.rating.score,
                        }
                        for s in report.suggestions[: args.max_suggestions]
                    ],
                    "breaksUniqueness": report.breaks_uniqueness,
                    "requiresSearch": report.breaks_solvability,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if not report.base_verdict.unique:
        print("puzzle is not valid (see `validate`); cannot harden")
        return 1
    assert report.base_rating is not None
    if not report.base_rating.solved_without_search:
        print("puzzle already requires search; cannot harden further")
        return 1
    base = report.base_rating
    print(f"current difficulty: {base.grade} (score {base.score})")
    if not report.suggestions:
        print("no single edit keeps the puzzle unique and search-free")
    else:
        shown = report.suggestions[: args.max_suggestions]
        print(f"top {len(shown)} suggestion(s):")
        for suggestion in shown:
            marker = "*" if suggestion.rating.score > base.score else " "
            print(f" {marker} {suggestion.describe()}")
        print("  (* = strictly harder than the current puzzle)")
    if report.breaks_uniqueness:
        print(f"cannot apply (solution would change or stop being unique): "
              f"{len(report.breaks_uniqueness)} edit(s)")
    if report.breaks_solvability:
        print(f"cannot apply (puzzle would require search): "
              f"{len(report.breaks_solvability)} edit(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="puzzle-analyzer",
        description=(
            "Validate logic puzzles with exact solution counting (Google "
            "OR-Tools CP-SAT and exhaustive search). Sudoku additionally "
            "gets annotated solving, difficulty grading and hardening."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("types", help="list supported puzzle types")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.set_defaults(func=cmd_types)

    p = sub.add_parser(
        "validate", help="prove a puzzle has exactly one solution"
    )
    p.add_argument("type", metavar="TYPE", help="puzzle type (see `types`)")
    p.add_argument(
        "spec",
        metavar="SPEC",
        help="JSON spec: file path, - for stdin, or inline JSON "
        "(sudoku also accepts an 81-char grid string)",
    )
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument(
        "--limit",
        type=int,
        default=2,
        metavar="N",
        help="enumerate up to N solutions (default 2, enough for a "
        "uniqueness proof)",
    )
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser(
        "grade", help="grade difficulty via the propagation engine"
    )
    p.add_argument("type", metavar="TYPE", help="puzzle type (see `types`)")
    p.add_argument("spec", metavar="SPEC", help="JSON spec (path, -, or inline)")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument(
        "--steps", action="store_true", help="print every annotated deduction"
    )
    p.set_defaults(func=cmd_grade)

    p = sub.add_parser(
        "harden",
        help="suggest edits that make the puzzle harder, same solution",
    )
    p.add_argument("type", metavar="TYPE", help="puzzle type (see `types`)")
    p.add_argument("spec", metavar="SPEC", help="JSON spec (path, -, or inline)")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument(
        "--max-suggestions", type=int, default=10, metavar="N",
        help="show at most N suggestions (default 10)",
    )
    p.add_argument(
        "--greedy", action="store_true",
        help="repeatedly apply the best edit and output the result",
    )
    p.add_argument(
        "--max-steps", type=int, default=None, metavar="N",
        help="with --greedy, stop after N edits",
    )
    p.set_defaults(func=cmd_harden)

    sudoku_cli.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

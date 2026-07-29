"""Command-line interface.

Usage examples::

    puzzle-analyzer types
    puzzle-analyzer validate kenken lattice.json
    puzzle-analyzer validate nonogram - < clues.json
    puzzle-analyzer validate sudoku "53..7....6..195...."
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

from .core.spec import SpecError
from .registry import PUZZLE_TYPES, get_puzzle_type
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
                    name: {"summary": t.summary, "foundIn": t.found_in}
                    for name, t in sorted(PUZZLE_TYPES.items())
                },
                indent=2,
            )
        )
        return 0
    width = max(len(name) for name in PUZZLE_TYPES)
    for name, puzzle_type in sorted(PUZZLE_TYPES.items()):
        print(f"{name:<{width}}  {puzzle_type.summary}")
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

    sudoku_cli.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

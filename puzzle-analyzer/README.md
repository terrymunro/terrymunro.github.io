# puzzle-analyzer

A Python toolkit for validating logic puzzles with **proofs, not
heuristics**, built on [Google OR-Tools](https://developers.google.com/optimization)
CP-SAT. Every supported puzzle type gets exact solution counting — no
solution, exactly one, or provably more than one. Sudoku additionally gets
an annotated no-guessing solver, difficulty grading, and hardening
suggestions.

Supports **every puzzle type on this site** (`index.html` — *The
Cartographer's Descent* — and `abyss.html` — *The Abyss*):

| Type | Site puzzles | Backend |
|---|---|---|
| `sudoku` | — | CP-SAT + human-technique solver |
| `nonogram` | The Loom, Blind Tomography | CP-SAT (automaton per line) |
| `skyscrapers` | Sluice Row | CP-SAT |
| `kenken` | Pressure Lattice | CP-SAT |
| `kakuro` | The Apothecary | CP-SAT |
| `starbattle` | The Aviary | CP-SAT |
| `bridges` | The Aqueduct | CP-SAT + connectivity check |
| `zebra` | The Reliquary, Switchyard Null | CP-SAT (clue DSL) |
| `truthlie` | False Choir | exhaustive enumeration |
| `cryptogram` | The Wax Seals, Dead Language | wordlist backtracking |
| `wordladder` | The Alchemist's Stair | wordlist path search |
| `balance` | The Assay Room | CP-SAT |

The test suite validates each module against the *actual puzzles and
published solutions* from both pages.

## Setup

Managed with [uv](https://docs.astral.sh/uv/) (Python 3.13+):

```sh
cd puzzle-analyzer
uv sync            # creates .venv with Python 3.13 and all dependencies
uv run pytest      # run the test suite
uv run ruff check .
```

## CLI

```sh
uv run puzzle-analyzer types                     # list supported types
uv run puzzle-analyzer validate TYPE SPEC        # prove exactly-one-solution
uv run puzzle-analyzer validate TYPE SPEC --json
```

`SPEC` is a JSON document — a file path, `-` for stdin, or inline JSON.
Each module's docstring documents its spec format
(`src/puzzle_analyzer/<type>.py`). For example:

```sh
uv run puzzle-analyzer validate kenken '{
  "size": 5,
  "cages": [{"label": "2×", "cells": [[0,0],[0,1]]}, ...]
}'
```

Exit codes: `0` proper puzzle (unique solution), `1` improper (zero or
multiple solutions, or malformed), `2` unusable spec.

### Sudoku commands

Sudoku keeps its richer command surface (an 81-character string, a file,
or `-`; `.` or `0` for blanks):

```sh
uv run puzzle-analyzer sudoku validate PUZZLE [--min-grade Hard] [--json]
uv run puzzle-analyzer sudoku solve PUZZLE       # annotated step-by-step
uv run puzzle-analyzer sudoku rate PUZZLE        # difficulty grade
uv run puzzle-analyzer sudoku harden PUZZLE [--greedy]
```

- **validate** proves uniqueness with CP-SAT *and* checks the puzzle is
  solvable without guessing by a human-technique solver (singles, locked
  candidates, subsets, fish, XY/XYZ-wings — applied cheapest-first, never
  backtracking). `--min-grade` turns the difficulty floor into an exit
  code for generator pipelines.
- **solve** prints every deduction with its justification, e.g.
  `[XY-Wing] pivot R7C9 {4,9} with pincers R3C9 {4,7} and R7C6 {7,9}: one
  pincer must be 7; eliminate 7 from R3C6`.
- **harden** suggests given-removals that keep the solution unique
  (re-proved per removal) and guess-free while raising difficulty;
  `--greedy` chains them — the classic Wikipedia easy puzzle goes from
  *Easy* (30 givens) to *Hard*, XY-Wing required (22 givens), in seconds.

## Library

```python
from puzzle_analyzer import get_puzzle_type

kenken = get_puzzle_type("kenken")
verdict = kenken.validate(kenken.parse(spec_dict))
verdict.unique          # True iff exactly one solution (proved)
verdict.solution        # the solution when unique
verdict.issues          # well-formedness problems, if any

# Sudoku extras
from puzzle_analyzer.sudoku import analyze, greedy_harden, parse_puzzle
analysis = analyze(parse_puzzle("53..7....6..195...."))
analysis.rating.grade                 # "Easy" … "Extreme"
for step in analysis.solve.steps:     # annotated deductions
    print(step.technique, step.description)
```

## Architecture

```
src/puzzle_analyzer/
├── core/            # shared infrastructure — the only cross-module dependency
│   ├── cpsat.py     #   CP-SAT model builder + exact solution enumeration
│   ├── verdict.py   #   the Verdict result type all validators return
│   ├── spec.py      #   friendly JSON-spec field parsing
│   └── wordlist.py  #   wordlist loading for dictionary-based puzzles
├── registry.py      # name → module mapping; the CLI's only coupling point
├── cli.py           # `types` / `validate` + sudoku subcommands
├── sudoku/          # the deep module: techniques, grading, hardening
└── <type>.py        # one cohesive module per puzzle type:
                     #   parse(spec) → puzzle, validate(puzzle) → Verdict
```

Design rules:

- **Loose coupling** — puzzle modules never import each other; they
  depend only on `core`. The CLI depends only on the registry.
- **High cohesion** — each module owns its type end to end: spec parsing,
  well-formedness checks, constraint model, solution rendering.
- **Uniform contract** — every module exposes `parse(spec)` and
  `validate(puzzle, *, limit) -> Verdict`, so adding a puzzle type is one
  new module plus one registry entry.
- **Exactness** — uniqueness is always proved by enumeration with a hard
  stop, never sampled. Constraints CP-SAT cannot express (bridge network
  connectivity) are enforced by filtering enumerated candidates, so
  counts stay exact.

## Tests

```sh
uv run pytest
```

The fixtures in `tests/fixtures/` are the genuine puzzles from
`index.html` and `abyss.html` with their published solutions. For each
type the suite checks that the real puzzle is proved unique and matches
its published solution, that under-cluing breaks uniqueness, that
contradictions yield zero solutions, and that malformed specs are
reported with useful messages. The sudoku suite additionally has a
soundness test asserting no solving technique ever eliminates a digit
belonging to the true solution.

CI runs ruff and the full suite on every pull request that touches this
directory (`.github/workflows/puzzle-analyzer-ci.yml`).

## Notes and limitations

- Cryptogram and word-ladder uniqueness is inherently **relative to a
  wordlist** — supply the lexicon the puzzle is meant to be judged
  against (a file path or inline list).
- Difficulty grading and hardening are sudoku-only today. The natural
  extension — a technique solver per type feeding the same `Rating`
  model — slots into the existing module boundaries without touching
  other types.
- Zebra and truth-lie clues use a structured JSON DSL rather than natural
  language; the fixtures show how each site clue translates.

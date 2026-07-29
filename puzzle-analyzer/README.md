# puzzle-analyzer

A Python toolkit for validating, grading and hardening logic puzzles with
**proofs, not heuristics**, built on
[Google OR-Tools](https://developers.google.com/optimization) CP-SAT and a
generic constraint-propagation engine. Every supported puzzle type gets:

- **exact solution counting** — no solution, exactly one, or provably more
  than one;
- **difficulty grading** with annotated deductions — how deep the
  reasoning must go, from pure propagation to what-if probing to
  full search;
- **hardening** (most types) — suggested edits that make the puzzle harder
  while provably preserving its unique solution and its no-guessing
  solvability.

Supports **every puzzle type on this site** (`index.html` — *The
Cartographer's Descent* — and `abyss.html` — *The Abyss*):

| Type | Site puzzles | Capabilities | Hardening move |
|---|---|---|---|
| `sudoku` | — | validate, grade, harden | remove a given |
| `nonogram` | The Loom, Blind Tomography | validate, grade, harden | hide a line clue |
| `skyscrapers` | Sluice Row | validate, grade, harden | blank a rim clue / clear a given |
| `kenken` | Pressure Lattice | validate, grade, harden | merge adjacent cages into `+` |
| `kakuro` | The Apothecary | validate, grade | — |
| `starbattle` | The Aviary | validate, grade | — (structure is the puzzle) |
| `bridges` | The Aqueduct | validate, grade, harden | hide an island's degree |
| `zebra` | The Reliquary, Switchyard Null | validate, grade, harden | drop a clue |
| `truthlie` | False Choir | validate, grade, harden | drop a statement |
| `cryptogram` | The Wax Seals, Dead Language | validate, grade, harden | withhold a given letter |
| `wordladder` | The Alchemist's Stair | validate, grade | — |
| `balance` | The Assay Room | validate, grade, harden | remove a balance |

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
uv run puzzle-analyzer types                     # list types + capabilities
uv run puzzle-analyzer validate TYPE SPEC        # prove exactly-one-solution
uv run puzzle-analyzer grade TYPE SPEC [--steps] # difficulty + deductions
uv run puzzle-analyzer harden TYPE SPEC [--greedy]
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

## Grading and hardening

Grading runs a **generic propagation engine** (`core/csp.py`): the puzzle
is decomposed into variables with finite domains plus local constraints
(explicit allowed-tuple tables, regular-language line automata, and
all-different groups). The engine solves the way a careful human does and
grades by how deep it had to go:

| Grade | Meaning |
|---|---|
| Easy | pure propagation, short inference chains |
| Medium | pure propagation, long inference chains |
| Hard | needed a few what-if probes (hypothesise, propagate, refute) |
| Very Hard | needed many probes |
| Extreme | propagation + probing insufficient: backtracking search required |

Every deduction is annotated (`grade TYPE SPEC --steps`), e.g.
`R8C4 = 1 — forced by row 8 clue [1, 1, 1, 2]` or `hypothesis R3C2 = 5
propagates to a contradiction; eliminate it`. Sudoku keeps its richer
human-technique grader (naked/hidden singles through XY-Wings) reporting
through the same `Rating` shape.

The engine's judgements line up with the pages' own claims, which the test
suite enforces: Blind Tomography solves in **exactly ten propagation
rounds with no branching** (as its solution notes state), Pressure Lattice
needs no guesses, and False Choir — whose intended solve is
branch-and-discard — grades Extreme.

Hardening (`core/hardening.py`) asks each module for its *reduction
moves* (see the table above), then for every candidate edit re-proves
uniqueness, re-checks that the solution is unchanged, and re-grades to
guarantee the puzzle never crosses into guessing territory. `--greedy`
chains the best strictly-improving edits. The suite verifies the engine
against ground truth here too: every one of tomography's 18 surviving
scans is correctly rejected as necessary, while all three of the Wax
Seals' given letters are correctly found removable.

```python
from puzzle_analyzer import get_puzzle_type
from puzzle_analyzer.core import hardening

zebra = get_puzzle_type("zebra")
puzzle = zebra.parse(spec_dict)
rating = zebra.grade(puzzle)          # Rating(grade, score, steps, ...)
report = hardening.suggest(
    puzzle,
    validate=zebra.validate,
    grade=zebra.grade,
    reductions=zebra.reductions,
    solution_key=zebra.solution_key,
)
report.suggestions                    # ranked, invariant-checked edits
```

## Architecture

```
src/puzzle_analyzer/
├── core/            # shared infrastructure — the only cross-module dependency
│   ├── cpsat.py     #   CP-SAT model builder + exact solution enumeration
│   ├── csp.py       #   propagation/probing engine for grading
│   ├── grading.py   #   the shared Rating scale
│   ├── hardening.py #   reduction-based hardening with invariant checks
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
  `validate(puzzle, *, limit) -> Verdict`; grading adds `grade(puzzle) ->
  Rating` and hardening adds `reductions(puzzle)` (plus an optional
  `solution_key`). The registry exposes each type's capabilities, so
  adding a puzzle type — or adding grading/hardening to one — is one
  module plus one registry entry, and the CLI picks it up automatically.
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
- Grades are relative to the engine's reasoning power (per-constraint
  propagation + one-level probing). A puzzle only solvable through global
  arguments the engine cannot propagate — e.g. bridges connectivity —
  grades Extreme, erring on the hard side, never the easy side.
- Star battle, kakuro and word ladder currently have no hardening moves:
  their clue structure has nothing that can be removed while keeping the
  puzzle well-formed. Adding a move later is one `reductions()` function.
- Zebra and truth-lie clues use a structured JSON DSL rather than natural
  language; the fixtures show how each site clue translates.

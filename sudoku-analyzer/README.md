# sudoku-analyzer

A Python tool for validating, grading, annotating and *hardening* sudoku
puzzles, built on [Google OR-Tools](https://developers.google.com/optimization)
and a guess-free human-technique solver.

It answers four questions about a puzzle:

1. **Is it a proper puzzle?** — well-formed givens and **exactly one
   solution**, proved with OR-Tools CP-SAT (it enumerates solutions and
   stops at two, so "unique" is a proof, not a heuristic).
2. **Is it solvable without guessing?** — a logical solver applies only
   named human techniques, never backtracks and never guesses. If it
   finishes, a human can too.
3. **How hard is it?** — every step is annotated with the technique that
   justified it, and the puzzle is graded by the hardest technique needed.
4. **Can it be made harder?** — suggests given-removals that keep the
   solution unique *and* keep the puzzle guess-free while raising the
   difficulty.

## Install

```sh
pip install -r requirements.txt   # just ortools (pytest optional, for tests)
```

Requires Python 3.9+.

## Usage

Puzzles are 81 characters (`1-9` givens, `0` or `.` blanks), a file path, or
`-` for stdin. Whitespace and ASCII grid decorations are ignored.

### Validate

```sh
python -m sudoku_analyzer validate "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
```

```
unique solution: yes (proved with OR-Tools CP-SAT)
solvable without guessing: yes
difficulty: Easy
hardest technique: Naked Single
...
```

Exit code is 0 only if the puzzle is unique **and** guess-free. Add
`--min-grade Hard` to also fail puzzles that are too easy — handy in a
generator pipeline. Add `--json` for machine-readable output (all
subcommands support it).

### Annotated solve

```sh
python -m sudoku_analyzer solve PUZZLE
```

Prints every step with its justification:

```
  8. [Locked Candidates (Pointing)] in box 2, digit 2 is confined to row 3 (R3C4,R3C6); eliminate 2 from R3C9
 ...
 17. [Naked Pair] cells R4C4,R5C5 in box 5 contain only {5,7}; eliminate 5 from R6C4; 7 from R4C6
 ...
 19. [XY-Wing] pivot R7C9 {4,9} with pincers R3C9 {4,7} and R7C6 {7,9}: one pincer must be 7; eliminate 7 from R3C6
```

### Harden

```sh
python -m sudoku_analyzer harden PUZZLE                 # rank single removals
python -m sudoku_analyzer harden PUZZLE --greedy        # apply the best chain
```

Removing a given never changes the solution grid — provided the puzzle stays
unique, which is re-proved with CP-SAT for every candidate removal. Each
candidate is also re-solved logically, so a suggestion is only made if the
harder puzzle still needs no guessing. Example: the classic Wikipedia "easy"
puzzle goes from *Easy* (30 givens, singles only) to *Hard* (22 givens,
XY-Wing required) in eight greedy removals, in a few seconds:

```
applied 8 removal(s):
  - remove the 9 at R2C5 -> Easy (hardest: Hidden Single, score 72.0)
  ...
  - remove the 6 at R2C1 -> Hard (hardest: XY-Wing, score 155.2)
```

The report also tells you which givens *cannot* be removed — because the
solution would stop being unique, or because the puzzle would start
requiring guesswork.

## Technique repertoire and grades

Applied cheapest-first, the way a human works:

| Grade | Techniques |
|---|---|
| Easy | Naked Single, Hidden Single |
| Medium | Locked Candidates (Pointing / Claiming), Naked Pair, Hidden Pair |
| Hard | Naked/Hidden Triple, X-Wing, XY-Wing, XYZ-Wing |
| Very Hard | Naked/Hidden Quad, Swordfish, Jellyfish |
| Extreme | beyond the repertoire — chains or trial-and-error needed |

"Extreme" puzzles are still validated for uniqueness, but the tool reports
them as **not** solvable without guessing (relative to this repertoire) and
refuses to harden into that territory.

The difficulty *score* is `sum of step costs + 10 × hardest step cost`, so
it orders variants of the same puzzle stably even within a grade.

## Library use

```python
from sudoku_analyzer import analyze, greedy_harden, parse_puzzle

analysis = analyze(parse_puzzle(puzzle_string))
analysis.valid                       # unique solution (CP-SAT proof)
analysis.solvable_without_guessing   # logical solver finished
analysis.rating.grade                # "Easy" ... "Extreme"
for step in analysis.solve.steps:    # annotated steps
    print(step.technique, step.description)

chain = greedy_harden(parse_puzzle(puzzle_string))
hardest_variant = chain[-1].new_puzzle
```

## Tests

```sh
python -m pytest tests/
```

Includes a soundness test asserting that no technique ever eliminates a
digit that belongs to the true (CP-SAT) solution.

## Design notes / limitations

- Uniqueness checking is exact; difficulty is inherently a model of human
  effort, so grades are relative to the implemented repertoire. Adding a
  technique (e.g. simple coloring, W-Wing, chains) is a matter of writing
  one finder function and registering it in `techniques.TECHNIQUES`.
- Hardening only *removes* givens, which is the only edit guaranteed to
  preserve the solution grid. A possible extension is swap-based search
  (remove one given, add a different solution cell) to escape local optima
  of the greedy chain.
- The greedy hardener re-proves uniqueness with CP-SAT at every step; on
  typical puzzles a full chain runs in seconds.

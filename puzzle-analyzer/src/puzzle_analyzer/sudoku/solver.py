"""Logical solver: applies human techniques and records every step."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from .board import Board
from .techniques import TECHNIQUES, Step


@dataclass(slots=True)
class SolveResult:
    solved: bool
    steps: list[Step]
    final_values: list[int]
    #: Name of the hardest technique used (None if no step was possible).
    hardest_technique: str | None
    #: Cost of the hardest technique used.
    hardest_cost: float
    #: Sum of step costs — a rough measure of total effort.
    total_cost: float
    technique_counts: dict[str, int] = field(default_factory=dict)
    #: Set when the board reached a contradictory state (invalid puzzle).
    contradiction: str | None = None

    @property
    def stalled(self) -> bool:
        """True if the solver got stuck with no contradiction: the puzzle
        needs techniques beyond the repertoire (chains / trial-and-error)."""
        return not self.solved and self.contradiction is None


def solve_logically(values: Sequence[int]) -> SolveResult:
    """Solve using only the human technique repertoire, cheapest-first.

    Never guesses and never backtracks.  If it finishes, the puzzle is
    solvable by pure logic with the implemented techniques.
    """
    board = Board(values)
    steps: list[Step] = []
    counts: dict[str, int] = {}
    hardest_cost = 0.0
    hardest_technique: str | None = None
    total_cost = 0.0

    while not board.is_solved():
        contradiction = board.find_contradiction()
        if contradiction:
            return SolveResult(
                solved=False,
                steps=steps,
                final_values=board.values,
                hardest_technique=hardest_technique,
                hardest_cost=hardest_cost,
                total_cost=total_cost,
                technique_counts=counts,
                contradiction=contradiction,
            )

        step = None
        cost = 0.0
        for technique in TECHNIQUES:
            step = technique.finder(board)
            if step is not None:
                cost = technique.cost
                break
        if step is None:
            break  # stalled: repertoire exhausted

        for cell, digit in step.placements:
            board.place(cell, digit)
        for cell, digit in step.eliminations:
            board.eliminate(cell, digit)

        steps.append(step)
        counts[step.technique] = counts.get(step.technique, 0) + 1
        total_cost += cost
        if cost > hardest_cost:
            hardest_cost = cost
            hardest_technique = step.technique

    return SolveResult(
        solved=board.is_solved(),
        steps=steps,
        final_values=board.values,
        hardest_technique=hardest_technique,
        hardest_cost=hardest_cost,
        total_cost=total_cost,
        technique_counts=counts,
    )

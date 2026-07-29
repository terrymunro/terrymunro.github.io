"""The result type every puzzle validator returns."""

from dataclasses import dataclass, field
from typing import Any

#: Sentinel count meaning "two or more" — enumeration stops at the limit,
#: so we never claim to know the exact number beyond it.
MULTIPLE = 2


@dataclass(frozen=True, slots=True)
class Verdict:
    """Outcome of validating a puzzle of any type.

    A puzzle is *proper* when it is well-formed and has exactly one
    solution.  ``solutions`` holds the enumerated solutions (up to the
    caller's limit) in a puzzle-specific rendering.
    """

    puzzle_type: str
    well_formed: bool
    issues: list[str] = field(default_factory=list)
    solution_count: int = 0
    solutions: list[Any] = field(default_factory=list)
    #: Optional puzzle-specific extras (e.g. sudoku difficulty grade).
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def unique(self) -> bool:
        return self.well_formed and self.solution_count == 1

    @property
    def solution(self) -> Any | None:
        return self.solutions[0] if self.unique else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "puzzleType": self.puzzle_type,
            "wellFormed": self.well_formed,
            "issues": self.issues,
            "solutionCount": (
                f"{MULTIPLE}+"
                if self.solution_count >= MULTIPLE
                else self.solution_count
            ),
            "unique": self.unique,
            "solution": self.solution,
            **self.details,
        }

    @staticmethod
    def malformed(puzzle_type: str, issues: list[str]) -> "Verdict":
        return Verdict(puzzle_type=puzzle_type, well_formed=False, issues=issues)

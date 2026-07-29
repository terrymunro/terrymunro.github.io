"""Difficulty grading on top of the propagation engine.

The grade reflects the deepest reasoning the engine needed:

* **Easy** — pure propagation, short inference chains.
* **Medium** — pure propagation, long inference chains.
* **Hard** — a few what-if probes were required.
* **Very Hard** — many probes were required.
* **Extreme** — propagation plus probing was not enough: solving needs
  backtracking search (guessing).

The numeric ``score`` orders variants of the same puzzle (higher =
harder), which is what the hardening engine optimises.  Sudoku uses its
own technique-based grader with the same grade scale and result shape.
"""

from dataclasses import dataclass, field
from typing import Any

from .csp import Csp, SolveReport, solve

GRADES = ["Easy", "Medium", "Hard", "Very Hard"]
EXTREME = "Extreme (requires backtracking search)"

#: Propagation solved it within this many waves -> Easy.
EASY_WAVE_LIMIT = 4
#: At most this many probe eliminations -> Hard; more -> Very Hard.
HARD_PROBE_LIMIT = 8


@dataclass(frozen=True, slots=True)
class Rating:
    """Uniform grading result shared by every puzzle type."""

    grade: str
    #: Comparable difficulty score; higher is harder.  Extreme ratings
    #: always outrank solvable ones.
    score: float
    solved_without_search: bool
    #: Annotated deductions (propagation assignments and probes).
    steps: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grade": self.grade,
            "score": self.score,
            "solvedWithoutSearch": self.solved_without_search,
            **self.detail,
        }


def rate_report(report: SolveReport) -> Rating:
    """Map a propagation-engine report onto the shared grade scale."""
    probe_eliminations = sum(1 for s in report.steps if s.kind == "probe")
    detail = {
        "waves": report.waves,
        "probeEliminations": probe_eliminations,
        "probesTried": report.probe_count,
    }
    steps = [f"[{s.kind}] {s.description}" for s in report.steps]

    if report.contradiction:
        return Rating(
            grade="Invalid",
            score=0.0,
            solved_without_search=False,
            steps=steps,
            detail={**detail, "contradiction": report.contradiction},
        )
    if not report.solved:
        score = 1000.0 + report.waves + 10 * probe_eliminations
        return Rating(
            grade=EXTREME,
            score=round(score, 1),
            solved_without_search=False,
            steps=steps,
            detail=detail,
        )

    score = report.waves + 10 * probe_eliminations
    if probe_eliminations == 0:
        grade = "Easy" if report.waves <= EASY_WAVE_LIMIT else "Medium"
    elif probe_eliminations <= HARD_PROBE_LIMIT:
        grade = "Hard"
    else:
        grade = "Very Hard"
    return Rating(
        grade=grade,
        score=round(score, 1),
        solved_without_search=True,
        steps=steps,
        detail=detail,
    )


def grade_csp(csp: Csp, *, max_probes: int = 2000) -> Rating:
    """Grade a puzzle from its CSP decomposition."""
    return rate_report(solve(csp, max_probes=max_probes))

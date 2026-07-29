"""Difficulty grading based on the techniques a logical solve required."""

from dataclasses import dataclass

from .solver import SolveResult

#: Grade thresholds on the *hardest* technique cost used in the solve.
#: See techniques.TECHNIQUES for the cost of each technique.
GRADES = [
    (1.5, "Easy"),        # singles only
    (3.4, "Medium"),      # locked candidates, pairs
    (5.0, "Hard"),        # triples, X-Wing, wings
    (6.0, "Very Hard"),   # quads, swordfish, jellyfish
]

#: Grade for puzzles the repertoire cannot finish without guessing.
BEYOND = "Extreme (requires chains or trial-and-error)"


@dataclass(frozen=True, slots=True)
class Rating:
    grade: str
    hardest_technique: str
    hardest_cost: float
    #: score = sum of step costs + 10 * hardest cost; comparable across
    #: variants of the same puzzle (higher = harder).
    score: float
    solvable_without_guessing: bool


def rate(result: SolveResult) -> Rating:
    """Grade a solve result.

    A stalled solve is graded ``BEYOND``: with this repertoire a human would
    need chains or trial-and-error.  Its score still reflects the progress
    made, plus a large constant so it always outranks solvable puzzles.
    """
    hardest = result.hardest_technique or "none"
    if result.solved:
        grade = GRADES[-1][1]
        for threshold, name in GRADES:
            if result.hardest_cost <= threshold:
                grade = name
                break
        score = result.total_cost + 10 * result.hardest_cost
        return Rating(grade, hardest, result.hardest_cost, round(score, 1), True)

    score = 1000 + result.total_cost + 10 * result.hardest_cost
    return Rating(BEYOND, hardest, result.hardest_cost, round(score, 1), False)

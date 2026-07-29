"""puzzle-analyzer: validate logic puzzles with proofs, not heuristics.

Every supported puzzle type gets exact solution counting (unique / none /
multiple), most via Google OR-Tools CP-SAT.  Sudoku additionally gets an
annotated no-guessing solver, difficulty grading and hardening suggestions.

See :mod:`puzzle_analyzer.registry` for the supported types and
:mod:`puzzle_analyzer.core` for the shared infrastructure.
"""

from .core import Verdict
from .registry import PUZZLE_TYPES, get_puzzle_type

__all__ = ["PUZZLE_TYPES", "Verdict", "get_puzzle_type"]

__version__ = "2.0.0"

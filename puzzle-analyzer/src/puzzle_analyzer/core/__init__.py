"""Shared infrastructure for all puzzle modules.

Puzzle modules depend only on this package (never on each other), keeping
coupling loose: each module owns its puzzle type end to end (parsing,
modelling, rendering) and delegates the generic parts — solution
enumeration, propagation-based grading, hardening bookkeeping and verdict
reporting — to the helpers here.
"""

from .cpsat import CpModelBuilder, enumerate_solutions
from .csp import (
    AllDifferentPropagator,
    Csp,
    RegularPropagator,
    TablePropagator,
    permutation_table,
    product_table,
)
from .grading import EXTREME, Rating, grade_csp
from .hardening import HardenReport, Reduction, Suggestion
from .verdict import MULTIPLE, Verdict
from .wordlist import load_wordlist

__all__ = [
    "EXTREME",
    "MULTIPLE",
    "AllDifferentPropagator",
    "CpModelBuilder",
    "Csp",
    "HardenReport",
    "Rating",
    "Reduction",
    "RegularPropagator",
    "Suggestion",
    "TablePropagator",
    "Verdict",
    "enumerate_solutions",
    "grade_csp",
    "load_wordlist",
    "permutation_table",
    "product_table",
]

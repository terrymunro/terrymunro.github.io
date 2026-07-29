"""Shared infrastructure for all puzzle modules.

Puzzle modules depend only on this package (never on each other), keeping
coupling loose: each module owns its puzzle type end to end (parsing,
modelling, rendering) and delegates the generic parts — solution
enumeration and verdict reporting — to the helpers here.
"""

from .cpsat import CpModelBuilder, enumerate_solutions
from .verdict import MULTIPLE, Verdict
from .wordlist import load_wordlist

__all__ = [
    "MULTIPLE",
    "CpModelBuilder",
    "Verdict",
    "enumerate_solutions",
    "load_wordlist",
]

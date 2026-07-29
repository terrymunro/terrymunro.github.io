"""Wordlist loading shared by the dictionary-based puzzle modules."""

from collections.abc import Iterable
from pathlib import Path


def load_wordlist(source: str | Path | Iterable[str]) -> frozenset[str]:
    """Load a wordlist from a file path or an iterable of words.

    Words are upper-cased and blank lines / ``#`` comments are ignored, so
    standard dictionary files (one word per line) work as-is.
    """
    if isinstance(source, str | Path):
        lines: Iterable[str] = Path(source).read_text(encoding="utf-8").splitlines()
    else:
        lines = source
    words = {
        word.upper()
        for line in lines
        if (word := line.strip()) and not word.startswith("#")
    }
    if not words:
        raise ValueError("wordlist is empty")
    return frozenset(words)

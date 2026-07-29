"""Import puzzles from the f-puzzles format.

f-puzzles (https://f-puzzles.com) is the de facto exchange format for
variant sudoku — Cracking the Cryptic links and SudokuPad both speak it.
A puzzle is a JSON document LZ-string-compressed into the ``?load=`` URL
parameter.

Only features this analyzer implements are accepted; anything else in the
document fails loudly with the list of unsupported features, so an import
can never silently drop a constraint (which would make "unique" claims
about the wrong puzzle).
"""

import json
import urllib.parse
from typing import Any

from lzstring import LZString

from ..core.spec import SpecError

#: Feature keys we translate into the analyzer's sudoku spec.
_HANDLED = {
    "size",
    "grid",
    "diagonal+",
    "diagonal-",
    "antiknight",
    "antiking",
    "killercage",
    "extraregion",
}
#: Metadata keys that carry no constraints and are safe to ignore.
_METADATA = {
    "title",
    "author",
    "ruleset",
    "solution",
    "highlightConflicts",
    "disabledlogic",
    "truecandidatesoptions",
}


def _cell_index(name: str) -> list[int]:
    """``"R4C7"`` -> ``[3, 6]`` (row, column, zero-based)."""
    try:
        row_part, col_part = name.upper().lstrip("R").split("C")
        r, c = int(row_part) - 1, int(col_part) - 1
    except ValueError as exc:
        raise SpecError(f"cannot parse cell reference {name!r}") from exc
    if not (0 <= r < 9 and 0 <= c < 9):
        raise SpecError(f"cell reference {name!r} is outside the grid")
    return [r, c]


def decode(source: str) -> dict[str, Any]:
    """Decode an f-puzzles URL (or bare payload) into a sudoku spec dict."""
    data = source.strip()
    if "?load=" in data:
        data = data.split("?load=", 1)[1]
    data = urllib.parse.unquote(data.split("&", 1)[0])
    text = LZString().decompressFromBase64(data)
    if not text:
        raise SpecError("could not decode f-puzzles data (not LZ-string base64)")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpecError(f"decoded f-puzzles data is not JSON: {exc}") from exc
    return convert(document)


def convert(document: dict[str, Any]) -> dict[str, Any]:
    """Translate a decoded f-puzzles JSON document into our spec format."""
    if document.get("size", 9) != 9:
        raise SpecError("only 9x9 f-puzzles grids are supported")
    unsupported = sorted(
        key
        for key, value in document.items()
        if key not in _HANDLED and key not in _METADATA and value
    )
    if unsupported:
        raise SpecError(
            "unsupported f-puzzles features: " + ", ".join(unsupported)
        )

    grid = document.get("grid")
    if not grid:
        raise SpecError("f-puzzles document has no grid")
    values = []
    for row in grid:
        for cell in row:
            cell = cell or {}
            if cell.get("region") is not None:
                raise SpecError(
                    "unsupported f-puzzles features: custom regions (jigsaw)"
                )
            values.append(
                int(cell["value"])
                if cell.get("given") and cell.get("value")
                else 0
            )
    if len(values) != 81:
        raise SpecError(f"f-puzzles grid has {len(values)} cells, expected 81")

    cages = []
    for cage in document.get("killercage") or []:
        if cage.get("value") in (None, ""):
            raise SpecError(
                "unsupported f-puzzles features: killer cage without a sum"
            )
        cages.append(
            {
                "cells": [_cell_index(c) for c in cage["cells"]],
                "sum": int(cage["value"]),
            }
        )

    spec: dict[str, Any] = {
        "givens": values,
        # f-puzzles: "diagonal-" is R1C1->R9C9, "diagonal+" is R9C1->R1C9.
        "diagonal_down": bool(document.get("diagonal-")),
        "diagonal_up": bool(document.get("diagonal+")),
        "antiknight": bool(document.get("antiknight")),
        "antiking": bool(document.get("antiking")),
        "cages": cages,
        "extra_regions": [
            [_cell_index(c) for c in region["cells"]]
            for region in document.get("extraregion") or []
        ],
    }
    if document.get("title"):
        spec["title"] = document["title"]
    if document.get("author"):
        spec["author"] = document["author"]
    return spec


def encode(spec: dict[str, Any]) -> str:
    """Encode our spec dict as an f-puzzles ``?load=`` payload.

    Mainly for tests (round-tripping) and for exporting puzzles authored
    here into f-puzzles/SudokuPad.
    """
    from .grid import parse_puzzle

    givens = spec.get("givens", "." * 81)
    values = parse_puzzle(givens) if isinstance(givens, str) else list(givens)
    document: dict[str, Any] = {
        "size": 9,
        "grid": [
            [
                {"value": values[r * 9 + c], "given": True}
                if values[r * 9 + c]
                else {}
                for c in range(9)
            ]
            for r in range(9)
        ],
    }
    if spec.get("diagonal_down"):
        document["diagonal-"] = True
    if spec.get("diagonal_up"):
        document["diagonal+"] = True
    for flag in ("antiknight", "antiking"):
        if spec.get(flag):
            document[flag] = True
    if spec.get("cages"):
        document["killercage"] = [
            {
                "cells": [f"R{r + 1}C{c + 1}" for r, c in cage["cells"]],
                "value": str(cage["sum"]),
            }
            for cage in spec["cages"]
        ]
    if spec.get("extra_regions"):
        document["extraregion"] = [
            {"cells": [f"R{r + 1}C{c + 1}" for r, c in region]}
            for region in spec["extra_regions"]
        ]
    return LZString().compressToBase64(json.dumps(document))

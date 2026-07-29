"""Shared test helpers.

Fixtures under ``tests/fixtures/`` are the actual puzzles published on the
site (index.html and abyss.html) together with their published solutions,
so the suite proves the analyzer agrees with ground truth end to end.
"""

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture() -> Any:
    def load(name: str) -> dict[str, Any]:
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

    return load

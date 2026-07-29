"""Helpers for parsing JSON puzzle specs with friendly error messages."""

from typing import Any


class SpecError(ValueError):
    """A puzzle spec is structurally invalid (wrong keys or types)."""


def get_field[T](
    spec: dict[str, Any],
    key: str,
    expected: type[T],
    default: T | None = None,
    *,
    required: bool = True,
) -> T:
    """Fetch ``spec[key]``, type-checked; ``default`` only applies when
    the field is not required."""
    if key not in spec:
        if required:
            raise SpecError(f"missing required field {key!r}")
        return default  # type: ignore[return-value]
    value = spec[key]
    if not isinstance(value, expected):
        raise SpecError(
            f"field {key!r} must be {expected.__name__}, "
            f"got {type(value).__name__}"
        )
    return value

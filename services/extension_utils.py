"""Utilities for working with file extension filters."""

from __future__ import annotations

from typing import Iterable


# Fix: Q-101
def normalise_extension_tokens(raw_extensions: Iterable[str]) -> tuple[str, ...]:
    """Normalise extension tokens for inclusion/exclusion filtering."""

    ordered_unique: dict[str, None] = {}

    for extension in raw_extensions:
        token = extension.strip().lower()
        if not token:
            continue
        if token in {"*", "*.*"}:
            ordered_unique.setdefault(token, None)
            continue
        if token.startswith("*."):
            token = token[1:]
        if not token.startswith("."):
            token = f".{token}"
        ordered_unique.setdefault(token, None)
    return tuple(ordered_unique.keys())


__all__ = ["normalise_extension_tokens"]

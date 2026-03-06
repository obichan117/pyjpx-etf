"""Shared terminal formatting helpers for the CLI."""

from __future__ import annotations

import unicodedata


def display_width(s: str) -> int:
    """Return the number of terminal columns a string occupies."""
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in s)


def pad(s: str, width: int) -> str:
    """Left-align *s* padded to *width* terminal columns."""
    return s + " " * (width - display_width(s))


def format_yen(value: int) -> str:
    """Format yen amount with Japanese unit suffixes (億/兆)."""
    oku = value / 1_0000_0000  # 億
    if oku >= 10000:  # >= 1兆
        cho = value / 1_0000_0000_0000
        s = f"{cho:.1f}".rstrip("0").rstrip(".")
        return f"{s}兆"
    if oku >= 100:
        return f"{oku:.0f}億"
    s = f"{oku:.2f}".rstrip("0").rstrip(".")
    return f"{s}億"

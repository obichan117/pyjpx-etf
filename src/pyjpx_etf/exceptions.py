"""Exception hierarchy for pyjpx-etf."""

__all__ = [
    "PyJPXETFError",
    "ETFNotFoundError",
    "FetchError",
    "ParseError",
    "DatabaseError",
]


class PyJPXETFError(Exception):
    """Base exception for all pyjpx-etf errors."""


class ETFNotFoundError(PyJPXETFError):
    """Raised when the ETF code is not found on any provider."""


class FetchError(PyJPXETFError):
    """Raised on network or HTTP errors."""


class ParseError(PyJPXETFError):
    """Raised when CSV content cannot be parsed."""


class DatabaseError(PyJPXETFError):
    """Raised when the local database is missing or corrupted."""

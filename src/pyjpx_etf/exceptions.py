"""Exception hierarchy for pyjpx-etf."""


class PyJPXETFError(Exception):
    """Base exception for all pyjpx-etf errors."""


class ETFNotFoundError(PyJPXETFError):
    """Raised when the ETF code is not found on any provider."""


class FetchError(PyJPXETFError):
    """Raised on network or HTTP errors."""


class ParseError(PyJPXETFError):
    """Raised when CSV content cannot be parsed."""

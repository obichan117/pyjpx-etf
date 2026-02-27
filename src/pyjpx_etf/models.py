"""Data models for ETF info and holdings."""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ETFInfo:
    """Metadata from the PCF header row."""

    code: str
    name: str
    cash_component: float
    shares_outstanding: int
    date: datetime.date

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Holding:
    """A single constituent holding in the ETF."""

    code: str
    name: str
    isin: str
    exchange: str
    currency: str
    shares: float
    price: float
    weight: float

    def to_dict(self) -> dict:
        return asdict(self)

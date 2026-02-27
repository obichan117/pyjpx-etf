"""Configuration for pyjpx-etf."""

from __future__ import annotations

from dataclasses import dataclass, field

_ICE_URL = "https://inav.ice.com/pcf-download/{code}.csv"
_SOLACTIVE_URL = (
    "https://www.solactive.com/downloads/etfservices/tse-pcf/single/{code}.csv"
)
_JPX_MASTER_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls"
)


@dataclass
class Config:
    """Mutable configuration for HTTP requests."""

    timeout: int = 30
    request_delay: float = 0.0
    provider_urls: list[str] = field(
        default_factory=lambda: [_ICE_URL, _SOLACTIVE_URL]
    )
    lang: str = "ja"


config = Config()

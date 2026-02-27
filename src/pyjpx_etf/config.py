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

_JPX_FEE_URL = "https://www.jpx.co.jp/equities/products/etfs/issues/01.html"

_ALIASES: dict[str, str] = {
    "topix": "1306",
    "225": "1321",
    "core30": "1311",
    "div50": "1489",
    "div70": "1577",
    "pbr": "2080",
    "sox": "2243",
    "jpsox1": "200A",
    "jpsox2": "2644",
}

_VALID_LANGS = ("ja", "en")


@dataclass
class Config:
    """Mutable configuration for HTTP requests."""

    timeout: int = 30
    request_delay: float = 0.0
    provider_urls: list[str] = field(
        default_factory=lambda: [_ICE_URL, _SOLACTIVE_URL]
    )
    _lang: str = field(default="ja", repr=False)

    @property
    def lang(self) -> str:
        return self._lang

    @lang.setter
    def lang(self, value: str) -> None:
        if value not in _VALID_LANGS:
            raise ValueError(f"lang must be one of {_VALID_LANGS}, got {value!r}")
        self._lang = value


config = Config()

"""Configuration for pyjpx-etf."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Config", "config"]

_ICE_URL = "https://inav.ice.com/pcf-download/{code}.csv"
_SOLACTIVE_URL = (
    "https://www.solactive.com/downloads/etfservices/tse-pcf/single/{code}.csv"
)
_SP_GLOBAL_URL = "https://api.ebs.ihsmarkit.com/inav/getfile?filename={code}.csv"
_JPX_MASTER_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls"
)

_JPX_FEE_URL = "https://www.jpx.co.jp/equities/products/etfs/issues/01.html"

_RAKUTEN_URL = "https://www.rakuten-sec.co.jp/web/market/search/etf_search/ETFD.csv"

_DB_RELEASE_BASE = "https://github.com/obichan117/pyjpx-etf/releases/download/db-latest"
# Latest-snapshot-only DB (a few MB) — the default `sync()` target.
_DB_LATEST_URL = f"{_DB_RELEASE_BASE}/pcf-latest.db.gz"
# Full append-only history DB (hundreds of MB) — `sync(full=True)` only.
_DB_FULL_URL = f"{_DB_RELEASE_BASE}/pcf-full.db.gz"
# Uncompressed full DB kept for clients <= 0.7.0 and as a fallback until the
# first pipeline run that publishes the .gz assets.
_DB_LEGACY_URL = f"{_DB_RELEASE_BASE}/pcf.db"

_UA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}

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
        default_factory=lambda: [_ICE_URL, _SOLACTIVE_URL, _SP_GLOBAL_URL]
    )
    db_path: Path | None = field(default=None, repr=False)
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

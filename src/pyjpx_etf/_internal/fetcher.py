"""HTTP fetching: ETF code → raw CSV text. No parsing."""

from __future__ import annotations

import time

import requests

from ..config import config
from ..exceptions import ETFNotFoundError, FetchError


def _looks_like_csv(text: str) -> bool:
    """Return True if the response text looks like a PCF CSV, not HTML."""
    stripped = text.strip()
    return not stripped.startswith("<") and "," in stripped


def fetch_pcf(code: str) -> str:
    """Fetch raw PCF CSV text, trying each provider URL in order.

    Raises ETFNotFoundError if all providers return 404.
    Raises FetchError on network or HTTP errors.
    """
    errors: list[Exception] = []

    for i, url_template in enumerate(config.provider_urls):
        if i > 0 and config.request_delay > 0:
            time.sleep(config.request_delay)

        url = url_template.format(code=code)
        try:
            response = requests.get(url, timeout=config.timeout)
        except requests.RequestException as e:
            errors.append(FetchError(f"Request failed for {url}: {e}"))
            continue

        if response.status_code == 200:
            if _looks_like_csv(response.text):
                return response.text
            errors.append(FetchError(f"Non-CSV response from {url}"))
            continue

        if response.status_code == 404:
            errors.append(ETFNotFoundError(f"ETF {code} not found at {url}"))
            continue

        errors.append(FetchError(f"HTTP {response.status_code} from {url}"))

    if not errors:
        raise FetchError("No provider URLs configured")

    # Only raise ETFNotFoundError if *all* errors are 404s
    if all(isinstance(e, ETFNotFoundError) for e in errors):
        raise ETFNotFoundError(
            f"ETF {code}: PCF data not found. "
            "The code may be invalid, the ETF may not be covered by "
            "available providers (ICE, Solactive), or the code may "
            "belong to an ETN (which has no PCF data)."
        )

    # Any non-CSV response present → likely outside data hours or unsupported code
    has_non_csv = any("Non-CSV" in str(e) for e in errors)
    if has_non_csv:
        raise FetchError(
            f"ETF {code}: no PCF data available right now. "
            "PCF data is published ~07:50–23:55 JST on business days only. "
            "If this persists, the code may not be covered by available providers."
        )

    # Raise the first non-404 error (server errors, network errors)
    for e in errors:
        if not isinstance(e, ETFNotFoundError):
            raise e

    raise FetchError(f"All providers failed for ETF {code}")

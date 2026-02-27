"""Pure CSV parsing: raw text → models. No I/O."""

from __future__ import annotations

import csv
import datetime
import io

from ..exceptions import ParseError
from ..models import ETFInfo, Holding


def parse_pcf(csv_text: str) -> tuple[ETFInfo, list[Holding]]:
    """Parse PCF CSV text into ETFInfo and a list of Holdings.

    The CSV has two sections separated by a blank line:
      Section 1 (header + 1 row): ETF metadata
      Section 2 (header + N rows): constituent holdings
    """
    sections = csv_text.replace("\r\n", "\n").strip().split("\n\n")
    if len(sections) < 2:
        raise ParseError("Expected two sections separated by a blank line")

    info = _parse_info_section(sections[0])
    holdings = _parse_holdings_section(sections[1])
    return info, holdings


def _parse_info_section(text: str) -> ETFInfo:
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    row = next(reader, None)

    if header is None or row is None:
        raise ParseError("ETF info section is incomplete")

    try:
        return ETFInfo(
            code=row[0].strip(),
            name=row[1].strip(),
            cash_component=float(row[2]),
            shares_outstanding=int(float(row[3])),
            date=datetime.datetime.strptime(row[4].strip(), "%Y%m%d").date(),
        )
    except (IndexError, ValueError) as e:
        raise ParseError(f"Failed to parse ETF info: {e}") from e


def _parse_holdings_section(text: str) -> list[Holding]:
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # skip header

    raw_holdings: list[dict] = []
    total_market_value = 0.0

    for row in reader:
        if len(row) < 7:
            continue
        try:
            shares = float(row[5])
            price = float(row[6])
        except ValueError:
            continue

        market_value = shares * price
        total_market_value += market_value
        raw_holdings.append(
            {
                "code": row[0].strip(),
                "name": row[1].strip(),
                "isin": row[2].strip(),
                "exchange": row[3].strip(),
                "currency": row[4].strip(),
                "shares": shares,
                "price": price,
                "market_value": market_value,
            }
        )

    if not raw_holdings:
        raise ParseError("No valid holdings found")

    holdings = []
    for h in raw_holdings:
        weight = h["market_value"] / total_market_value if total_market_value else 0.0
        holdings.append(
            Holding(
                code=h["code"],
                name=h["name"],
                isin=h["isin"],
                exchange=h["exchange"],
                currency=h["currency"],
                shares=h["shares"],
                price=h["price"],
                weight=weight,
            )
        )

    return holdings

"""Pure computation: OHLCV signal derivation and screening logic.

No I/O, no extras dependency — importable with pandas alone.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROLLING_WINDOW = 20

# Stats that require OHLCV data
OHLCV_STATS = {
    "turnover": "Daily turnover (yen)",
    "turnover_ratio": "Today's turnover vs 20-day avg",
    "range_pct": "Daily range as % of close",
    "atr": "20-day average of range_pct",
    "range_ratio": "Today's range vs avg",
    "vol_ratio": "Today's volume vs 20-day avg",
    "return_pct": "Daily return %",
}

# Stats from DB only (no OHLCV needed)
DB_STATS = {
    "aum": "Total net asset value (yen)",
    "fee": "Annual expense ratio %",
}

STATS = {**OHLCV_STATS, **DB_STATS}

DEFAULT_STAT = "range_pct"

# Stats where lower is better (sort ascending)
ASCENDING_STATS = {"fee"}


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------


def _compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["atr"] = df["range_pct"].rolling(ROLLING_WINDOW).mean()
    df["range_ratio"] = df["range_pct"] / df["atr"]
    df["vol_ratio"] = df["volume"] / df["volume"].rolling(ROLLING_WINDOW).mean()
    df["return_pct"] = df["close"].pct_change() * 100
    df["turnover"] = df["close"] * df["volume"]
    df["turnover_ratio"] = (
        df["turnover"] / df["turnover"].rolling(ROLLING_WINDOW).mean()
    )
    return df


def _safe_round(val: object, decimals: int = 2) -> float | None:
    if pd.isna(val):
        return None
    return round(float(val), decimals)


def _screen(
    ohlcv: dict[str, pd.DataFrame],
    names: dict[str, str],
    fees: dict[str, float],
    aum: dict[str, float],
    sort_by: str,
    top: int,
) -> pd.DataFrame:
    rows = []

    # DB-only stats: build rows from DB data, no OHLCV needed
    if sort_by in DB_STATS:
        for code in set(list(aum.keys()) + list(fees.keys())):
            rows.append(
                {
                    "code": code,
                    "name": names.get(code, ""),
                    "aum": aum.get(code),
                    "fee": fees.get(code),
                }
            )
    else:
        # OHLCV-based stats
        for code, df in ohlcv.items():
            if len(df) < ROLLING_WINDOW + 1:
                continue
            signals = _compute_signals(df)
            latest = signals.iloc[-1]
            if pd.isna(latest.get(sort_by)):
                continue
            rows.append(
                {
                    "code": code,
                    "name": names.get(code, ""),
                    "date": latest["date"],
                    "close": latest["close"],
                    "turnover": _safe_round(latest["turnover"], 0),
                    "turnover_ratio": _safe_round(latest["turnover_ratio"], 2),
                    "range_pct": _safe_round(latest["range_pct"], 2),
                    "atr": _safe_round(latest["atr"], 2),
                    "range_ratio": _safe_round(latest["range_ratio"], 2),
                    "vol_ratio": _safe_round(latest["vol_ratio"], 2),
                    "return_pct": _safe_round(latest["return_pct"], 2),
                    "volume": int(latest["volume"]),
                    "aum": aum.get(code),
                    "fee": fees.get(code),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    # Filter rows where sort column is missing
    if sort_by in result.columns:
        result = result.dropna(subset=[sort_by])

    # Sort
    ascending = sort_by in ASCENDING_STATS
    if sort_by == "return_pct":
        result["_sort"] = result[sort_by].abs()
        result = result.sort_values("_sort", ascending=False).drop(columns=["_sort"])
    else:
        result = result.sort_values(sort_by, ascending=ascending)

    return result.head(top).reset_index(drop=True)

"""Fetch and backfill OHLCV data for trade classification."""

from __future__ import annotations

import contextlib
import csv
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from lafmm.quant.types import Bar

HEADER = ("date", "open", "high", "low", "close", "volume")
TRADING_TO_CALENDAR = 1.5


# ── Fetch ──────────────────────────────────────────────────────────


def fetch_bars(ticker: str, start: date, end: date) -> list[Bar]:
    import yfinance as yf

    data = yf.download(
        ticker,
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False,
    )
    if data is None or data.empty:
        return []
    if hasattr(data.columns, "droplevel"):
        with contextlib.suppress(IndexError, ValueError):
            data.columns = data.columns.droplevel(1)
    ohlcv = data[["Open", "High", "Low", "Close", "Volume"]]
    return [
        Bar(
            date=str(ohlcv.index[i])[:10],
            open=round(float(ohlcv.iat[i, 0]), 2),
            high=round(float(ohlcv.iat[i, 1]), 2),
            low=round(float(ohlcv.iat[i, 2]), 2),
            close=round(float(ohlcv.iat[i, 3]), 2),
            volume=int(ohlcv.iat[i, 4]),
        )
        for i in range(len(ohlcv))
    ]


# ── Read / Write ──────────────────────────────────────────────────


def read_existing_dates(ticker_dir: Path) -> set[str]:
    dates: set[str] = set()
    if not ticker_dir.is_dir():
        return dates
    for csv_file in ticker_dir.glob("*.csv"):
        with csv_file.open() as f:
            dates.update(row["date"] for row in csv.DictReader(f))
    return dates


def _bar_to_row(bar: Bar) -> list[str | int]:
    return [
        bar.date,
        f"{bar.open:.2f}",
        f"{bar.high:.2f}",
        f"{bar.low:.2f}",
        f"{bar.close:.2f}",
        bar.volume,
    ]


def _write_year(csv_path: Path, bars: Sequence[Bar]) -> int:
    existing = set()
    if csv_path.exists():
        with csv_path.open() as f:
            existing = {row["date"] for row in csv.DictReader(f)}
    new_bars = [bar for bar in bars if bar.date not in existing]
    if not new_bars:
        return 0
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(HEADER)
        for bar in sorted(new_bars, key=lambda b: b.date):
            writer.writerow(_bar_to_row(bar))
    return len(new_bars)


def write_bars(ticker_dir: Path, bars: Sequence[Bar]) -> int:
    ticker_dir.mkdir(parents=True, exist_ok=True)
    by_year: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        by_year[bar.date[:4]].append(bar)
    return sum(
        _write_year(ticker_dir / f"{year}.csv", year_bars)
        for year, year_bars in sorted(by_year.items())
    )


# ── Discovery ─────────────────────────────────────────────────────


def _parse_symbols_from_table(text: str) -> set[str]:
    symbols: set[str] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("| time "):
            in_table = True
            continue
        if line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 2:
                symbols.add(parts[1].upper())
        elif in_table:
            in_table = False
    return symbols


def _traded_symbols(account_dir: Path) -> set[str]:
    journal = account_dir / "journal"
    if not journal.exists():
        return set()
    symbols: set[str] = set()
    for md_file in journal.rglob("*.md"):
        symbols |= _parse_symbols_from_table(md_file.read_text())
    return symbols


def find_ticker_dir(data_dir: Path, symbol: str) -> Path | None:
    for group_dir in sorted(data_dir.iterdir()):
        if not group_dir.is_dir() or group_dir.name.startswith("."):
            continue
        ticker_dir = group_dir / symbol
        if ticker_dir.is_dir() and any(ticker_dir.glob("*.csv")):
            return ticker_dir
    return None


REGIME_TICKERS: dict[str, str] = {
    "^VIX": "VIX",
    "^VIX3M": "VIX3M",
}


def _ref_dir(data_dir: Path) -> Path:
    for group_dir in sorted(data_dir.iterdir()):
        if not group_dir.is_dir() or group_dir.name.startswith("."):
            continue
        ref = group_dir / "_ref"
        if ref.is_dir():
            return ref
    return data_dir / "us-indices" / "_ref"


# ── Public API ─────────────────────────────────────────────────────


def ensure_regime_data(
    data_dir: Path,
    min_bars: int = 250,
) -> list[str]:
    ref = _ref_dir(data_dir)
    end = date.today() + timedelta(days=1)
    calendar_days = int(min_bars * TRADING_TO_CALENDAR)
    start = end - timedelta(days=calendar_days)

    updated: list[str] = []
    for yahoo_ticker, local_name in REGIME_TICKERS.items():
        ticker_dir = ref / local_name
        existing = read_existing_dates(ticker_dir)
        if len(existing) >= min_bars:
            continue
        bars = fetch_bars(yahoo_ticker, start, end)
        if not bars:
            print(f"fetch {local_name}: no data", file=sys.stderr)
            continue
        new_bars = [bar for bar in bars if bar.date not in existing]
        if not new_bars:
            continue
        added = write_bars(ticker_dir, new_bars)
        if added > 0:
            updated.append(local_name)
    return updated


def ensure_history(
    account_dir: Path,
    data_dir: Path,
    min_bars: int = 250,
) -> list[str]:
    traded = _traded_symbols(account_dir)
    if not traded:
        return []

    end = date.today() + timedelta(days=1)
    calendar_days = int(min_bars * TRADING_TO_CALENDAR)
    start = end - timedelta(days=calendar_days)

    updated: list[str] = []
    for symbol in sorted(traded):
        ticker_dir = find_ticker_dir(data_dir, symbol)
        if ticker_dir is None:
            ticker_dir = data_dir / "_adhoc" / symbol

        existing = read_existing_dates(ticker_dir)
        if len(existing) >= min_bars:
            continue

        bars = fetch_bars(symbol, start, end)
        if not bars:
            print(f"fetch {symbol}: no data", file=sys.stderr)
            continue

        new_bars = [bar for bar in bars if bar.date not in existing]
        if not new_bars:
            continue

        added = write_bars(ticker_dir, new_bars)
        if added > 0:
            updated.append(symbol)

    return updated

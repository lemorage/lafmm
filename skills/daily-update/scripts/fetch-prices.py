#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["yfinance"]
# ///
"""Fetch daily OHLCV prices and append to LAFMM CSV files.

Usage:
    uv run fetch.py TICKER [--csv PATH] [--start DATE] [--days N]

Examples:
    uv run fetch.py NVDA                           # append latest to ~/.lafmm/data/*/NVDA/YYYY.csv
    uv run fetch.py NVDA --csv data/semis/NVDA     # explicit ticker dir
    uv run fetch.py NVDA --start 2026-01-02        # backfill from date
    uv run fetch.py NVDA --days 30                 # last 30 calendar days

CSVs are partitioned by year: each ticker gets a directory with one CSV per year.
Format: date,open,high,low,close,volume (OHLCV).
Output is always appended — existing rows are preserved, duplicates skipped.

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from lafmm.fetch import fetch_bars, find_ticker_dir, read_existing_dates, write_bars
from lafmm.quant.types import Bar

if TYPE_CHECKING:
    from _csv import _writer

HEADER = ["date", "open", "high", "low", "close", "volume"]


def _write_bar_with_echo(writer: _writer, bar: Bar) -> None:
    row = [
        bar.date,
        f"{bar.open:.2f}",
        f"{bar.high:.2f}",
        f"{bar.low:.2f}",
        f"{bar.close:.2f}",
        bar.volume,
    ]
    writer.writerow(row)
    print(",".join(str(v) for v in row))


def append_bars_flat(csv_path: Path, bars: Sequence[Bar]) -> int:
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(HEADER)
        for bar in bars:
            _write_bar_with_echo(writer, bar)
    return len(bars)


def resolve_target(ticker: str, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    from lafmm.init import HUMAN_DATA, get_root

    root = get_root()
    data_dir = root / HUMAN_DATA if root else Path.home() / ".lafmm" / "data"
    if data_dir.exists():
        found = find_ticker_dir(data_dir, ticker)
        if found is not None:
            return found
    return Path.cwd() / ticker


def resolve_start_date(
    explicit_start: date | None,
    days: int | None,
    existing_dates: set[str],
) -> date:
    today = date.today()
    if explicit_start is not None:
        return explicit_start
    if days is not None:
        return today - timedelta(days=days)
    if existing_dates:
        return date.fromisoformat(max(existing_dates)) + timedelta(days=1)
    return today - timedelta(days=60)


def run_fetch(ticker: str, target: Path, start: date) -> None:
    today = date.today()
    if start > today:
        print(f"already up to date (last: {start - timedelta(days=1)})")
        sys.exit(0)

    existing_dates = read_existing_dates(target)
    bars = fetch_bars(ticker, start, today + timedelta(days=1))
    new_bars = sorted(
        [b for b in bars if b.date not in existing_dates],
        key=lambda b: b.date,
    )

    if not new_bars:
        last = max(existing_dates) if existing_dates else "empty"
        print(f"{ticker}: no new data (has through {last})")
        sys.exit(0)

    if target.is_dir() or not target.suffix:
        added = write_bars(target, new_bars)
    else:
        added = append_bars_flat(target, new_bars)

    total = len(existing_dates) + added
    print(f"\n{ticker}: +{added} rows → {target} (total: {total})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch daily OHLCV prices for LAFMM")
    parser.add_argument("ticker", help="stock ticker symbol (e.g. NVDA)")
    parser.add_argument("--csv", type=Path, default=None, help="path to ticker dir or CSV file")
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=None,
        help="start date (YYYY-MM-DD)",
    )
    parser.add_argument("--days", type=int, default=None, help="fetch last N calendar days")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    target = resolve_target(ticker, args.csv)
    existing = read_existing_dates(target)
    start = resolve_start_date(args.start, args.days, existing)
    run_fetch(ticker, target, start)


if __name__ == "__main__":
    main()

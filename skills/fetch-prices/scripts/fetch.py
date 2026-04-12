#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["yfinance"]
# ///
"""Fetch daily closing prices and append to LAFMM CSV files.

Usage:
    uv run fetch.py TICKER [--csv PATH] [--start DATE] [--days N]

Examples:
    uv run fetch.py NVDA                           # append latest to ~/.lafmm/data/*/NVDA/YYYY.csv
    uv run fetch.py NVDA --csv data/semis/NVDA.csv # explicit path
    uv run fetch.py NVDA --start 2026-01-02        # backfill from date
    uv run fetch.py NVDA --days 30                 # last 30 calendar days

CSVs are partitioned by year: each ticker gets a directory with one CSV per year.
Output is always appended — existing rows are preserved, duplicates skipped.
Prints each new row added so the agent can see what changed.

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf


def fetch_prices(ticker: str, start: date, end: date) -> Sequence[tuple[str, float]]:
    data = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False)
    if data is None or data.empty:
        return []
    close = data["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    import pandas as pd

    return [
        (pd.Timestamp(ts).strftime("%Y-%m-%d"), round(float(val), 2))
        for ts, val in zip(close.index, close.values, strict=True)
    ]


def read_existing_dates(path: Path) -> set[str]:
    if path.is_dir():
        dates: set[str] = set()
        for csv_file in path.glob("*.csv"):
            with csv_file.open() as f:
                dates.update(row["date"] for row in csv.DictReader(f))
        return dates
    if path.is_file():
        with path.open() as f:
            return {row["date"] for row in csv.DictReader(f)}
    return set()


def append_rows_partitioned(ticker_dir: Path, rows: Sequence[tuple[str, float]]) -> int:
    ticker_dir.mkdir(parents=True, exist_ok=True)
    by_year: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for d, price in rows:
        year = d[:4]
        by_year[year].append((d, price))

    added = 0
    for year, year_rows in sorted(by_year.items()):
        csv_path = ticker_dir / f"{year}.csv"
        is_new = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", newline="") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["date", "price"])
            for d, price in year_rows:
                writer.writerow([d, f"{price:.2f}"])
                print(f"{d},{price:.2f}")
                added += 1
    return added


def append_rows_flat(csv_path: Path, rows: Sequence[tuple[str, float]]) -> int:
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["date", "price"])
        for d, price in rows:
            writer.writerow([d, f"{price:.2f}"])
            print(f"{d},{price:.2f}")
    return len(rows)


def find_ticker_dir(ticker: str) -> Path | None:
    lafmm_data = Path.home() / ".lafmm" / "data"
    if not lafmm_data.exists():
        return None
    for group_dir in sorted(lafmm_data.iterdir()):
        if not group_dir.is_dir():
            continue
        candidate = group_dir / ticker
        if candidate.is_dir():
            return candidate
    return None


def resolve_target(ticker: str, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    if found := find_ticker_dir(ticker):
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
    rows = fetch_prices(ticker, start, today + timedelta(days=1))
    new_rows = sorted(
        [(d, p) for d, p in rows if d not in existing_dates],
        key=lambda r: r[0],
    )

    if not new_rows:
        last = max(existing_dates) if existing_dates else "empty"
        print(f"{ticker}: no new data (has through {last})")
        sys.exit(0)

    if target.is_dir() or not target.suffix:
        added = append_rows_partitioned(target, new_rows)
    else:
        added = append_rows_flat(target, new_rows)

    total = len(existing_dates) + added
    print(f"\n{ticker}: +{added} rows → {target} (total: {total})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch daily prices for LAFMM")
    parser.add_argument("ticker", help="stock ticker symbol (e.g. NVDA)")
    parser.add_argument("--csv", type=Path, default=None, help="path to CSV file or ticker dir")
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

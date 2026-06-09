"""Fetch and backfill OHLCV data for trade classification."""

from __future__ import annotations

import contextlib
import csv
import random
import sys
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lafmm.quant.types import Bar

HEADER = ("date", "open", "high", "low", "close", "volume")
TRADING_TO_CALENDAR = 1.5
MIN_BARS = 250

THROTTLE_BASE: float = 0.8
THROTTLE_JITTER: float = 0.4
_MAX_CONSECUTIVE_FAILURES: int = 2


# ── Split Adjustment ──────────────────────────────────────────────

_SPLITS_APPLIED = ".splits_applied"


def _read_applied_splits(ticker_dir: Path) -> set[str]:
    marker = ticker_dir / _SPLITS_APPLIED
    if not marker.exists():
        return set()
    return set(marker.read_text().splitlines())


def _record_applied_split(ticker_dir: Path, split_date: str) -> None:
    marker = ticker_dir / _SPLITS_APPLIED
    applied = _read_applied_splits(ticker_dir)
    applied.add(split_date)
    marker.write_text("\n".join(sorted(applied)) + "\n")


def _unapplied_splits(
    symbol: str,
    since: str,
    already_applied: set[str],
) -> list[tuple[str, float]]:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    splits = ticker.splits
    if splits is None or splits.empty:
        return []
    return [
        (str(splits.index[i])[:10], float(splits.iloc[i]))
        for i in range(len(splits))
        if str(splits.index[i])[:10] > since and str(splits.index[i])[:10] not in already_applied
    ]


def _adjust_csv_for_split(csv_path: Path, ratio: float) -> None:
    rows: list[dict[str, str]] = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        return
    tmp = csv_path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(
                [
                    row["date"],
                    f"{float(row['open']) / ratio:.2f}",
                    f"{float(row['high']) / ratio:.2f}",
                    f"{float(row['low']) / ratio:.2f}",
                    f"{float(row['close']) / ratio:.2f}",
                    int(float(row["volume"]) * ratio),
                ]
            )
    tmp.replace(csv_path)


def _apply_splits(ticker_dir: Path, symbol: str, existing: frozenset[str]) -> None:
    if not existing:
        return
    last_date = max(existing)
    applied = _read_applied_splits(ticker_dir)
    splits = _unapplied_splits(symbol, last_date, applied)
    if not splits:
        return
    for split_date, ratio in splits:
        print(
            f"split detected: {symbol} {ratio}:1 on {split_date}",
            file=sys.stderr,
        )
        for csv_file in ticker_dir.glob("*.csv"):
            _adjust_csv_for_split(csv_file, ratio)
        _record_applied_split(ticker_dir, split_date)


# ── Rate Limiting ──────────────────────────────────────────────────


def throttle() -> None:
    time.sleep(THROTTLE_BASE + random.uniform(-THROTTLE_JITTER, THROTTLE_JITTER))


@dataclass(frozen=True, slots=True)
class _BackfillTarget:
    symbol: str
    ticker_dir: Path
    label: str
    existing: frozenset[str]


def _throttled_backfill(
    items: Sequence[_BackfillTarget],
    start: date,
    end: date,
) -> list[tuple[str, int]]:
    updated: list[tuple[str, int]] = []
    consecutive_empty_fetches = 0
    for i, item in enumerate(items):
        if i > 0:
            throttle()
        bars = fetch_bars(item.symbol, start, end)
        if not bars:
            consecutive_empty_fetches += 1
            print(f"fetch {item.label}: no data", file=sys.stderr)
            if consecutive_empty_fetches >= _MAX_CONSECUTIVE_FAILURES:
                print("rate limited — aborting", file=sys.stderr)
                break
            continue
        consecutive_empty_fetches = 0
        _apply_splits(item.ticker_dir, item.symbol, item.existing)
        new_bars = [bar for bar in bars if bar.date not in item.existing]
        if not new_bars:
            continue
        added = write_bars(item.ticker_dir, new_bars)
        if added > 0:
            updated.append((item.label, len(item.existing) + added))
    return updated


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
    return [
        Bar(
            date=str(data.index[i])[:10],
            open=round(float(data["Open"].iloc[i]), 2),
            high=round(float(data["High"].iloc[i]), 2),
            low=round(float(data["Low"].iloc[i]), 2),
            close=round(float(data["Close"].iloc[i]), 2),
            volume=int(data["Volume"].iloc[i]),
        )
        for i in range(len(data))
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

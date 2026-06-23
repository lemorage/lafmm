#!/usr/bin/env python3
"""Fetch daily OHLCV prices and append to LAFMM CSV files.

Usage:
    ./run .claude/skills/daily-update/scripts/fetch-prices.py
    ./run .claude/skills/daily-update/scripts/fetch-prices.py TICKER [TICKER ...]
    ./run .claude/skills/daily-update/scripts/fetch-prices.py --group semis

With no arguments, fetches all tracked tickers across all groups.
With tickers, fetches only those. With --group, fetches that group.

By default, only tickers missing today's bar are fetched. Use --all to
force-fetch everything regardless. Use --days N for explicit backfill
window (e.g., new-group warmup).

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from lafmm.fetch import (
    MIN_BARS,
    REGIME_TICKERS,
    TRADING_TO_CALENDAR,
    _BackfillTarget,
    _ref_dir,
    _throttled_backfill,
    find_ticker_dir,
    read_existing_dates,
)


def _data_dir() -> Path:
    from lafmm.init import HUMAN_DATA, get_root

    root = get_root()
    return root / HUMAN_DATA if root else Path.home() / ".lafmm" / "data"


_SKIP_DIRS = {"_meta", "_ref"}


def _discover_regime(data_dir: Path) -> list[_BackfillTarget]:
    ref_dir = _ref_dir(data_dir)
    targets: list[_BackfillTarget] = []
    for yahoo_ticker, local_name in REGIME_TICKERS.items():
        ticker_dir = ref_dir / local_name
        existing = read_existing_dates(ticker_dir)
        targets.append(_BackfillTarget(yahoo_ticker, ticker_dir, local_name, frozenset(existing)))
    return targets


def _discover_all(data_dir: Path) -> list[_BackfillTarget]:
    items: list[_BackfillTarget] = _discover_regime(data_dir)
    for group_dir in sorted(data_dir.iterdir()):
        if not group_dir.is_dir() or group_dir.name.startswith("."):
            continue
        if group_dir.name in _SKIP_DIRS:
            continue
        items.extend(_discover_group(group_dir))
    return items


def _discover_group(group_dir: Path) -> list[_BackfillTarget]:
    items: list[_BackfillTarget] = []
    for ticker_dir in sorted(group_dir.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name.startswith((".", "_")):
            continue
        if not any(ticker_dir.glob("*.csv")):
            continue
        existing = read_existing_dates(ticker_dir)
        label = f"{group_dir.name}/{ticker_dir.name}"
        items.append(_BackfillTarget(ticker_dir.name, ticker_dir, label, frozenset(existing)))
    return items


def _resolve_ticker_dir(data_dir: Path, symbol: str) -> Path:
    found = find_ticker_dir(data_dir, symbol)
    if found is not None:
        return found
    for group_dir in sorted(data_dir.iterdir()):
        if not group_dir.is_dir() or group_dir.name in _SKIP_DIRS:
            continue
        candidate = group_dir / symbol
        if candidate.is_dir():
            return candidate
    print(f"{symbol}: no group dir, using _adhoc", file=sys.stderr)
    return data_dir / "_adhoc" / symbol


def _discover_tickers(data_dir: Path, tickers: list[str]) -> list[_BackfillTarget]:
    items: list[_BackfillTarget] = []
    for symbol in tickers:
        ticker_dir = _resolve_ticker_dir(data_dir, symbol)
        existing = read_existing_dates(ticker_dir)
        items.append(_BackfillTarget(symbol, ticker_dir, symbol, frozenset(existing)))
    return items


def _missing_today(items: list[_BackfillTarget]) -> list[_BackfillTarget]:
    today = date.today().isoformat()
    return [item for item in items if not item.existing or max(item.existing) < today]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch daily OHLCV prices")
    parser.add_argument("tickers", nargs="*", help="ticker symbols (omit for all)")
    parser.add_argument("--group", default=None, help="fetch a specific group")
    parser.add_argument(
        "--all", action="store_true", help="force fetch all, even if today's bar exists"
    )
    parser.add_argument("--days", type=int, default=None, help="lookback in calendar days")
    args = parser.parse_args()

    data_dir = _data_dir()
    if not data_dir.exists():
        print("no data directory found", file=sys.stderr)
        sys.exit(1)

    if args.tickers:
        items = _discover_tickers(data_dir, [t.upper() for t in args.tickers])
    elif args.group:
        group_dir = data_dir / args.group
        if not group_dir.is_dir():
            print(f"group not found: {args.group}", file=sys.stderr)
            sys.exit(1)
        items = _discover_group(group_dir)
    else:
        items = _discover_all(data_dir)

    if not args.all:
        items = _missing_today(items)

    if not items:
        print("all tickers up to date")
        sys.exit(0)

    print(f"fetching {len(items)} tickers...")
    end = date.today() + timedelta(days=1)
    if args.days:
        lookback = args.days
    elif any(not item.existing for item in items):
        lookback = int(MIN_BARS * TRADING_TO_CALENDAR)
    else:
        lookback = 60
    start = end - timedelta(days=lookback)
    updated = _throttled_backfill(items, start, end)

    if updated:
        for label, total in updated:
            print(f"  {label}: {total} bars")
        print(f"\nupdated {len(updated)}/{len(items)} tickers")
    else:
        print("no new data available")


if __name__ == "__main__":
    main()

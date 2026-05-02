#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["yfinance"]
# ///
"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

DEFAULT_HORIZON_DAYS = 14
_CACHE_FILENAME = "_earnings.json"
_META_DIR = "_meta"


@dataclass(frozen=True, slots=True)
class EarningsEvent:
    ticker: str
    group: str
    earnings_date: str
    days_until: int


def _fetch_earnings_date(ticker: str) -> str | None:
    import yfinance as yf

    try:
        earnings_calendar = yf.Ticker(ticker).calendar
    except Exception:
        return None
    if not earnings_calendar or not isinstance(earnings_calendar, dict):
        return None
    dates = earnings_calendar.get("Earnings Date")
    if not dates:
        return None
    first = dates[0] if isinstance(dates, list) else dates
    return str(first)[:10]


def _collect_tickers(
    data_dir: Path,
    group_filter: str | None = None,
) -> Sequence[tuple[str, str]]:
    ticker_group_pairs: list[tuple[str, str]] = []
    for group_dir in sorted(data_dir.iterdir()):
        if group_filter and group_dir.name != group_filter:
            continue
        toml_path = group_dir / "group.toml"
        if not toml_path.exists():
            continue
        with toml_path.open("rb") as f:
            config = tomllib.load(f)
        group_name = config.get("name", group_dir.name)
        for ticker_dir in sorted(group_dir.iterdir()):
            if ticker_dir.is_dir() and ticker_dir.name != "_ref":
                ticker_group_pairs.append((ticker_dir.name.upper(), group_name))
    return ticker_group_pairs


def _build_event(
    ticker: str,
    group: str,
    date_str: str,
    today: date,
    horizon_end: date,
) -> EarningsEvent | None:
    try:
        earnings = date.fromisoformat(date_str)
    except ValueError:
        return None
    if not (today <= earnings <= horizon_end):
        return None
    return EarningsEvent(
        ticker=ticker,
        group=group,
        earnings_date=date_str,
        days_until=(earnings - today).days,
    )


def _load_earnings_cache(data_dir: Path) -> dict[str, str]:
    cache_path = data_dir / _META_DIR / _CACHE_FILENAME
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text())


def _save_earnings_cache(data_dir: Path, cache: dict[str, str]) -> None:
    meta_dir = data_dir / _META_DIR
    meta_dir.mkdir(parents=True, exist_ok=True)
    cache_path = meta_dir / _CACHE_FILENAME
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def _resolve_earnings_date(
    ticker: str,
    cache: dict[str, str],
    today: date,
) -> str | None:
    cached = cache.get(ticker)
    if cached is not None:
        try:
            if date.fromisoformat(cached) >= today:
                return cached
        except ValueError:
            pass
    fetched = _fetch_earnings_date(ticker)
    if fetched is not None:
        cache[ticker] = fetched
    elif ticker in cache:
        del cache[ticker]
    return fetched


def _scan_earnings(
    data_dir: Path,
    horizon_days: int,
    group_filter: str | None = None,
) -> Sequence[EarningsEvent]:
    today = date.today()
    horizon_end = today + timedelta(days=horizon_days)
    tickers = _collect_tickers(data_dir, group_filter)
    cache = _load_earnings_cache(data_dir)
    events: list[EarningsEvent] = []
    for ticker, group in tickers:
        date_str = _resolve_earnings_date(ticker, cache, today)
        if date_str is None:
            continue
        event = _build_event(ticker, group, date_str, today, horizon_end)
        if event is not None:
            events.append(event)
    _save_earnings_cache(data_dir, cache)
    events.sort(key=lambda e: (e.earnings_date, e.ticker))
    return events


def _print_report(events: Sequence[EarningsEvent], horizon_days: int) -> None:
    if not events:
        print(f"No tracked tickers report earnings in the next {horizon_days} days.")
        return
    print(f"Upcoming earnings (next {horizon_days} days):")
    print()
    for event in events:
        days_label = "tomorrow" if event.days_until == 1 else f"in {event.days_until} days"
        if event.days_until == 0:
            days_label = "TODAY"
        print(f"  {event.ticker:<6} ({event.group})")
        print(f"         {event.earnings_date}  {days_label}")


_COLORS: tuple[str, ...] = ("cyan", "magenta", "yellow", "green", "blue", "red")

_ANSI: dict[str, str] = {
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "red": "\033[31m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _print_calendar(events: Sequence[EarningsEvent]) -> None:
    if not events:
        print("No upcoming earnings.")
        return
    first_date = date.fromisoformat(events[0].earnings_date)
    year, month = first_date.year, first_date.month
    month_events = [e for e in events if date.fromisoformat(e.earnings_date).month == month]
    day_colors = _assign_day_colors(month_events)
    title = f"{calendar.month_name[month]} {year}"
    print(f"    {title:^20}")
    _print_month_grid(year, month, day_colors)
    print()
    _print_calendar_legend(month_events, day_colors)


def _assign_day_colors(events: Sequence[EarningsEvent]) -> dict[int, str]:
    days_seen: dict[int, str] = {}
    color_idx = 0
    for event in events:
        day = date.fromisoformat(event.earnings_date).day
        if day not in days_seen:
            days_seen[day] = _COLORS[color_idx % len(_COLORS)]
            color_idx += 1
    return days_seen


def _print_month_grid(year: int, month: int, day_colors: dict[int, str]) -> None:
    calendar.setfirstweekday(calendar.SUNDAY)
    print("Su Mo Tu We Th Fr Sa")
    for week in calendar.monthcalendar(year, month):
        cells = [_format_day(day, day_colors) for day in week]
        print("".join(cells))


def _format_day(day: int, day_colors: dict[int, str]) -> str:
    if day == 0:
        return "   "
    color_name = day_colors.get(day)
    if color_name is not None:
        ansi = _ANSI[color_name]
        return f"{ansi}{_ANSI['bold']}{day:>2}{_ANSI['reset']} "
    return f"{day:>2} "


def _print_calendar_legend(
    events: Sequence[EarningsEvent],
    day_colors: dict[int, str],
) -> None:
    by_date: dict[str, list[str]] = {}
    for event in events:
        by_date.setdefault(event.earnings_date, []).append(event.ticker)
    reset = _ANSI["reset"]
    for date_str, tickers in by_date.items():
        day = date.fromisoformat(date_str).day
        color_name = day_colors[day]
        ansi = _ANSI[color_name]
        print(f"  {ansi}■{reset} {', '.join(tickers)}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upcoming earnings for tracked LAFMM tickers",
    )
    parser.add_argument("data_dir", type=Path, help="path to data directory")
    parser.add_argument("--group", "-g", default=None, help="scan only this group")
    parser.add_argument("--days", type=int, default=DEFAULT_HORIZON_DAYS)
    parser.add_argument("--cal", action="store_true", help="calendar grid view")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    if not data_dir.exists():
        print(f"error: {data_dir} not found", file=sys.stderr)
        sys.exit(1)
    events = _scan_earnings(data_dir, args.days, args.group)
    if args.json:
        print(json.dumps([asdict(e) for e in events], indent=2))
    elif args.cal:
        _print_calendar(events)
    else:
        _print_report(events, args.days)


if __name__ == "__main__":
    main()

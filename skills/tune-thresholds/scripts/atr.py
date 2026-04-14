#!/usr/bin/env python3
"""Compute ATR-based swing thresholds for a LAFMM group.

Usage:
    uv run atr.py GROUP_DIR [--period N] [--multiplier X]

Examples:
    uv run atr.py ~/.lafmm/data/semis
    uv run atr.py ~/.lafmm/data/us-indices --period 20
    uv run atr.py ~/.lafmm/data/energy --multiplier 2.0

Reads OHLCV CSVs from the group's leader ticker directories,
computes ATR for each leader, and suggests swing_pct / confirm_pct
values for group.toml. Does not modify any files.

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PERIOD = 14
DEFAULT_MULTIPLIER = 1.5


@dataclass(frozen=True, slots=True)
class Bar:
    date: str
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class AtrResult:
    ticker: str
    atr: float
    atr_pct: float
    last_close: float
    bar_count: int


def load_bars(ticker_dir: Path) -> Sequence[Bar]:
    rows: list[Bar] = []
    for csv_file in sorted(ticker_dir.glob("*.csv")):
        with csv_file.open() as f:
            for row in csv.DictReader(f):
                rows.append(
                    Bar(
                        date=row["date"],
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                    )
                )
    rows.sort(key=lambda b: b.date)
    return rows


def compute_true_ranges(bars: Sequence[Bar]) -> Sequence[float]:
    if len(bars) < 2:
        return []
    return [
        max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - bars[i - 1].close),
            abs(bars[i].low - bars[i - 1].close),
        )
        for i in range(1, len(bars))
    ]


def compute_atr(bars: Sequence[Bar], period: int) -> AtrResult | None:
    if not bars:
        return None
    ranges = compute_true_ranges(bars)
    if len(ranges) < period:
        return None
    atr = sum(ranges[-period:]) / period
    last_close = bars[-1].close
    atr_pct = (atr / last_close) * 100 if last_close > 0 else 0.0
    return AtrResult(
        ticker="",
        atr=round(atr, 2),
        atr_pct=round(atr_pct, 2),
        last_close=round(last_close, 2),
        bar_count=len(bars),
    )


def read_group_config(
    group_dir: Path,
) -> tuple[str, tuple[str, str], float, float]:
    toml_path = group_dir / "group.toml"
    if not toml_path.exists():
        print(f"error: {toml_path} not found", file=sys.stderr)
        sys.exit(1)
    with toml_path.open("rb") as f:
        raw = tomllib.load(f)
    name = raw.get("name", group_dir.name)
    leaders = (raw["leaders"][0], raw["leaders"][1])
    swing_pct = float(raw.get("swing_pct", 5.0))
    confirm_pct = float(raw.get("confirm_pct", 2.5))
    return name, leaders, swing_pct, confirm_pct


def analyze_leader(
    group_dir: Path,
    ticker: str,
    period: int,
) -> AtrResult | None:
    ticker_dir = group_dir / ticker
    if not ticker_dir.is_dir():
        ticker_dir = group_dir / ticker.upper()
    if not ticker_dir.is_dir():
        print(f"  {ticker}: no data directory found", file=sys.stderr)
        return None
    bars = load_bars(ticker_dir)
    if not bars:
        print(f"  {ticker}: no price data", file=sys.stderr)
        return None
    result = compute_atr(bars, period)
    if result is None:
        min_bars = period + 1
        print(f"  {ticker}: need {min_bars} bars, have {len(bars)}")
        return None
    return AtrResult(
        ticker=ticker,
        atr=result.atr,
        atr_pct=result.atr_pct,
        last_close=result.last_close,
        bar_count=result.bar_count,
    )


def print_leader_line(result: AtrResult, period: int) -> None:
    print(
        f"  {result.ticker:<6} ATR({period}): "
        f"${result.atr:<8} -> {result.atr_pct}% of "
        f"${result.last_close}  ({result.bar_count} bars)"
    )


def print_warnings(
    current_swing: float,
    higher: AtrResult,
) -> None:
    ratio = current_swing / higher.atr_pct if higher.atr_pct > 0 else 0
    if ratio < 1.1:
        print(
            f"  Warning: current {current_swing}% barely exceeds "
            f"{higher.ticker}'s noise band {higher.atr_pct}%."
        )
        print("  Risk of false column transitions.")
    elif ratio > 2.5:
        print(
            f"  Warning: current {current_swing}% is {ratio:.1f}x the noise band {higher.atr_pct}%."
        )
        print("  Risk of missing real trend changes.")


def print_report(
    group_name: str,
    group_dir: Path,
    leaders: tuple[str, str],
    results: Sequence[AtrResult],
    current_swing: float,
    current_confirm: float,
    period: int,
    multiplier: float,
) -> None:
    print(f"Group: {group_name} ({group_dir})")
    print(f"Leaders: {leaders[0]}, {leaders[1]}")
    print(f"ATR period: {period}")
    print()

    for r in results:
        print_leader_line(r, period)
    print()

    higher = max(results, key=lambda r: r.atr_pct)
    suggested_swing = round(higher.atr_pct * multiplier, 1)
    suggested_confirm = round(suggested_swing / 2, 1)

    print(f"  Current:     swing_pct = {current_swing}   confirm_pct = {current_confirm}")
    print(f"  Suggested:   swing_pct = {suggested_swing}   confirm_pct = {suggested_confirm}")
    print()
    print(f"  Based on: {higher.ticker} ATR% = {higher.atr_pct}% x {multiplier} multiplier")

    print_warnings(current_swing, higher)


def suggest_thresholds(
    results: Sequence[AtrResult],
    multiplier: float,
) -> tuple[float, float]:
    higher = max(results, key=lambda r: r.atr_pct)
    swing = round(higher.atr_pct * multiplier, 1)
    return swing, round(swing / 2, 1)


def print_json(
    results: Sequence[AtrResult],
    multiplier: float,
) -> None:
    swing, confirm = suggest_thresholds(results, multiplier)
    output = {
        "swing_pct": swing,
        "confirm_pct": confirm,
        "leaders": [
            {
                "ticker": r.ticker,
                "atr": r.atr,
                "atr_pct": r.atr_pct,
                "last_close": r.last_close,
                "bar_count": r.bar_count,
            }
            for r in results
        ],
    }
    print(json.dumps(output))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ATR-based threshold tuning for LAFMM",
    )
    parser.add_argument(
        "group_dir",
        type=Path,
        help="path to group directory",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=DEFAULT_PERIOD,
        help=f"ATR period (default: {DEFAULT_PERIOD})",
    )
    parser.add_argument(
        "--multiplier",
        type=float,
        default=DEFAULT_MULTIPLIER,
        help=f"ATR-to-swing multiplier (default: {DEFAULT_MULTIPLIER})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output machine-readable JSON",
    )
    args = parser.parse_args()

    group_dir = args.group_dir.expanduser().resolve()
    name, leaders, current_swing, current_confirm = read_group_config(group_dir)

    results: list[AtrResult] = []
    for ticker in leaders:
        result = analyze_leader(group_dir, ticker, args.period)
        if result is not None:
            results.append(result)

    if not results:
        print(
            "error: no ATR data for any leader. run fetch-prices first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.json:
        print_json(results, args.multiplier)
    else:
        print_report(
            name,
            group_dir,
            leaders,
            results,
            current_swing,
            current_confirm,
            args.period,
            args.multiplier,
        )


if __name__ == "__main__":
    main()

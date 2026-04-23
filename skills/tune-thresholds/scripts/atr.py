#!/usr/bin/env python3
"""ATR-based threshold tuning for LAFMM groups.

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lafmm.loader import load_group_config, load_price_series
from lafmm.quant.volatility import atr, atr_pct

DEFAULT_PERIOD = 14
DEFAULT_MULTIPLIER = 1.5


@dataclass(frozen=True, slots=True)
class LeaderResult:
    ticker: str
    atr: float
    atr_pct: float
    last_close: float
    bar_count: int


def _analyze_leader(
    group_dir: Path,
    ticker: str,
    period: int,
) -> LeaderResult | None:
    ticker_dir = group_dir / ticker
    if not ticker_dir.is_dir():
        ticker_dir = group_dir / ticker.upper()
    if not ticker_dir.is_dir():
        print(f"  {ticker}: no data directory found", file=sys.stderr)
        return None
    series = load_price_series(ticker_dir)
    if series is None:
        print(f"  {ticker}: no price data", file=sys.stderr)
        return None
    atr_val = atr(series, period)
    pct_val = atr_pct(series, period)
    if atr_val is None or pct_val is None:
        print(f"  {ticker}: need {period + 1} bars, have {len(series.close)}")
        return None
    return LeaderResult(
        ticker=ticker,
        atr=round(atr_val, 2),
        atr_pct=round(pct_val, 2),
        last_close=round(series.close[-1], 2),
        bar_count=len(series.close),
    )


def _suggest_thresholds(
    results: Sequence[LeaderResult],
    multiplier: float,
) -> tuple[float, float, LeaderResult]:
    higher = max(results, key=lambda r: r.atr_pct)
    swing = round(higher.atr_pct * multiplier, 1)
    return swing, round(swing / 2, 1), higher


def _print_leader_lines(results: Sequence[LeaderResult], period: int) -> None:
    for r in results:
        print(
            f"  {r.ticker:<6} ATR({period}): "
            f"${r.atr:<8} -> {r.atr_pct}% of "
            f"${r.last_close}  ({r.bar_count} bars)"
        )


def _print_warnings(current_swing: float, higher: LeaderResult) -> None:
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


def _print_report(
    config_name: str,
    group_dir: Path,
    results: Sequence[LeaderResult],
    current_swing: float,
    current_confirm: float,
    period: int,
    multiplier: float,
) -> None:
    print(f"Group: {config_name} ({group_dir})")
    print(f"ATR period: {period}")
    print()
    _print_leader_lines(results, period)
    print()
    swing, confirm, higher = _suggest_thresholds(results, multiplier)
    print(f"  Current:     swing_pct = {current_swing}   confirm_pct = {current_confirm}")
    print(f"  Suggested:   swing_pct = {swing}   confirm_pct = {confirm}")
    print()
    print(f"  Based on: {higher.ticker} ATR% = {higher.atr_pct}% x {multiplier} multiplier")
    _print_warnings(current_swing, higher)


def _print_json(results: Sequence[LeaderResult], multiplier: float) -> None:
    swing, confirm, _ = _suggest_thresholds(results, multiplier)
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
    parser = argparse.ArgumentParser(description="ATR-based threshold tuning for LAFMM")
    parser.add_argument("group_dir", type=Path, help="path to group directory")
    parser.add_argument("--period", type=int, default=DEFAULT_PERIOD)
    parser.add_argument("--multiplier", type=float, default=DEFAULT_MULTIPLIER)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    group_dir = args.group_dir.expanduser().resolve()
    config = load_group_config(group_dir)

    results: list[LeaderResult] = []
    for ticker in config.leaders:
        result = _analyze_leader(group_dir, ticker, args.period)
        if result is not None:
            results.append(result)

    if not results:
        print("error: no ATR data for any leader. run fetch-prices first.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        _print_json(results, args.multiplier)
    else:
        _print_report(
            config.name,
            group_dir,
            results,
            config.swing_pct,
            config.confirm_pct,
            args.period,
            args.multiplier,
        )


if __name__ == "__main__":
    main()

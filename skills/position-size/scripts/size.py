#!/usr/bin/env python3
"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from lafmm.loader import load_group_config, load_price_series
from lafmm.quant.risk import (
    DrawdownResult,
    drawdown_percentile,
    half_kelly,
    max_drawdown,
    monte_carlo_drawdown,
)
from lafmm.quant.types import to_returns

DEFAULT_SIMULATIONS = 1000
DEFAULT_HORIZON = 252
DEFAULT_SEED = 42
PERCENTILE_TIERS: tuple[int, ...] = (50, 75, 95, 99)


def _resolve_ticker_dir(group_dir: Path, ticker: str) -> Path | None:
    ticker_dir = group_dir / ticker
    if ticker_dir.is_dir():
        return ticker_dir
    ticker_dir = group_dir / ticker.upper()
    return ticker_dir if ticker_dir.is_dir() else None


def _analyze_drawdown(group_dir: Path, ticker: str) -> DrawdownResult | None:
    ticker_dir = _resolve_ticker_dir(group_dir, ticker)
    if ticker_dir is None:
        return None
    series = load_price_series(ticker_dir)
    if series is None:
        return None
    returns = to_returns(series)
    return max_drawdown(returns)


def _print_kelly(win_rate: float, win_loss_ratio: float) -> None:
    fraction = half_kelly(win_rate, win_loss_ratio)
    print(f"  Win rate:        {win_rate:.0%}")
    print(f"  Win/loss ratio:  {win_loss_ratio:.2f}")
    print(f"  Half-Kelly:      {fraction:.1%} of capital per trade")
    if fraction <= 0:
        print("  Signal has no edge. Do not size.")


def _print_drawdown_report(
    group_name: str,
    results: Sequence[tuple[str, DrawdownResult | None]],
    monte_carlo_percentiles: Mapping[str, float] | None,
) -> None:
    print(f"Group: {group_name}")
    print()
    for ticker, drawdown_result in results:
        if drawdown_result is not None:
            print(
                f"  {ticker}: max drawdown {drawdown_result.depth:.1%} "
                f"({drawdown_result.start_date} to {drawdown_result.end_date})"
            )
        else:
            print(f"  {ticker}: insufficient data")
    if monte_carlo_percentiles:
        print()
        print("  Monte Carlo (forward-looking, 1yr horizon):")
        for label, value in monte_carlo_percentiles.items():
            print(f"    {label}: {value:.1%}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Position sizing for LAFMM")
    subparsers = parser.add_subparsers(dest="command")
    kelly_p = subparsers.add_parser("kelly", help="half-Kelly from win rate + ratio")
    kelly_p.add_argument("win_rate", type=float, help="e.g. 0.65")
    kelly_p.add_argument("win_loss_ratio", type=float, help="e.g. 1.5")
    dd_p = subparsers.add_parser("drawdown", help="historical + Monte Carlo drawdown")
    dd_p.add_argument("group_dir", type=Path)
    dd_p.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    dd_p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    dd_p.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    match args.command:
        case "kelly":
            _print_kelly(args.win_rate, args.win_loss_ratio)
        case "drawdown":
            _run_drawdown(args)
        case _:
            parser.print_help()
            sys.exit(1)


def _run_drawdown(args: argparse.Namespace) -> None:
    group_dir = args.group_dir.expanduser().resolve()
    config = load_group_config(group_dir)

    results: list[tuple[str, DrawdownResult | None]] = [
        (ticker, _analyze_drawdown(group_dir, ticker)) for ticker in config.leaders
    ]
    results = [(ticker, result) for ticker, result in results if result is not None]

    if not results:
        print("error: no data for any leader.", file=sys.stderr)
        sys.exit(1)

    monte_carlo_percentiles = _run_monte_carlo(group_dir, config.leaders[0], args)

    if args.json:
        _emit_json(config.name, results, monte_carlo_percentiles)
    else:
        _print_drawdown_report(config.name, results, monte_carlo_percentiles)


def _emit_json(
    group_name: str,
    results: Sequence[tuple[str, DrawdownResult | None]],
    monte_carlo_percentiles: Mapping[str, float] | None,
) -> None:
    leaders = [
        {"ticker": ticker, **dataclasses.asdict(result)}
        for ticker, result in results
        if result is not None
    ]
    output: dict[str, object] = {"group": group_name, "leaders": leaders}
    if monte_carlo_percentiles:
        output["monte_carlo"] = dict(monte_carlo_percentiles)
    print(json.dumps(output, indent=2))


def _run_monte_carlo(
    group_dir: Path,
    ticker: str,
    args: argparse.Namespace,
) -> dict[str, float] | None:
    ticker_dir = _resolve_ticker_dir(group_dir, ticker)
    if ticker_dir is None:
        return None
    series = load_price_series(ticker_dir)
    if series is None:
        return None
    returns = to_returns(series)
    drawdowns = monte_carlo_drawdown(returns, args.simulations, args.horizon, seed=DEFAULT_SEED)
    if not drawdowns:
        return None
    return {f"{p}th": drawdown_percentile(drawdowns, p) for p in PERCENTILE_TIERS}


if __name__ == "__main__":
    main()

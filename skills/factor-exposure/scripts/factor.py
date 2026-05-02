#!/usr/bin/env python3
"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lafmm.loader import load_group_config, load_price_series
from lafmm.quant.factor import factor_regression
from lafmm.quant.types import PriceSeries, to_returns

Z_SCORE_95 = 1.96
Z_SCORE_99 = 2.58


@dataclass(frozen=True, slots=True)
class ExposureResult:
    ticker: str
    alpha: float
    alpha_tstat: float
    market_beta: float
    r_squared: float
    bar_count: int


def _find_benchmark(data_root: Path) -> Path | None:
    benchmark_paths = [
        data_root / "us-indices" / "SPY",
        data_root / "us-indices" / "spy",
    ]
    for candidate in benchmark_paths:
        if candidate.is_dir():
            return candidate
    return None


def _resolve_ticker_dir(group_dir: Path, ticker: str) -> Path | None:
    ticker_dir = group_dir / ticker
    if ticker_dir.is_dir():
        return ticker_dir
    ticker_dir = group_dir / ticker.upper()
    return ticker_dir if ticker_dir.is_dir() else None


def _analyze_leader(
    group_dir: Path,
    ticker: str,
    benchmark_dir: Path,
) -> ExposureResult | None:
    ticker_dir = _resolve_ticker_dir(group_dir, ticker)
    if ticker_dir is None:
        print(f"  {ticker}: no data directory found", file=sys.stderr)
        return None
    series = load_price_series(ticker_dir)
    benchmark_series = load_price_series(benchmark_dir)
    if series is None or benchmark_series is None:
        print(f"  {ticker}: insufficient data", file=sys.stderr)
        return None
    return _run_regression(ticker, series, benchmark_series)


def _run_regression(
    ticker: str,
    series: PriceSeries,
    benchmark_series: PriceSeries,
) -> ExposureResult | None:
    strategy_returns = to_returns(series)
    market_returns = to_returns(benchmark_series)
    result = factor_regression(strategy_returns, market_returns)
    if result is None:
        print(f"  {ticker}: regression failed (too few overlapping dates)", file=sys.stderr)
        return None
    return ExposureResult(
        ticker=ticker,
        alpha=result.alpha,
        alpha_tstat=result.alpha_tstat,
        market_beta=result.betas[0] if result.betas else 0.0,
        r_squared=result.r_squared,
        bar_count=len(series.close),
    )


def _significance_stars(tstat: float) -> str:
    if abs(tstat) > Z_SCORE_99:
        return "***"
    if abs(tstat) > Z_SCORE_95:
        return "**"
    return ""


def _print_leader(result: ExposureResult) -> None:
    alpha_pct = result.alpha * 100
    stars = _significance_stars(result.alpha_tstat)
    print(f"  {result.ticker:<6} alpha: {alpha_pct:+.2f}%/yr {stars}  (t={result.alpha_tstat:.2f})")
    print(
        f"         beta:  {result.market_beta:.2f}"
        f"   R²: {result.r_squared:.2f}"
        f"   ({result.bar_count} bars)"
    )


def _print_report(group_name: str, results: Sequence[ExposureResult]) -> None:
    print(f"Group: {group_name}")
    print("Benchmark: SPY")
    print()
    for result in results:
        _print_leader(result)
    print()
    _print_verdict(results)


def _print_verdict(results: Sequence[ExposureResult]) -> None:
    for result in results:
        if abs(result.alpha_tstat) < Z_SCORE_95:
            print(f"  {result.ticker}: alpha not significant.")
        elif result.alpha > 0:
            print(f"  {result.ticker}: positive alpha. Genuine edge beyond market beta.")
        else:
            print(f"  {result.ticker}: negative alpha. Underperforming vs market exposure.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Factor exposure for LAFMM group")
    parser.add_argument("group_dir", type=Path, help="path to group directory")
    parser.add_argument("--benchmark", type=Path, default=None, help="benchmark ticker dir")
    parser.add_argument("--json", action="store_true")
    return parser


def _resolve_benchmark(data_root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    return _find_benchmark(data_root)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    group_dir = args.group_dir.expanduser().resolve()
    config = load_group_config(group_dir)

    benchmark_dir = _resolve_benchmark(group_dir.parent, args.benchmark)
    if benchmark_dir is None:
        print("error: SPY not found in data/us-indices/. Specify --benchmark.", file=sys.stderr)
        sys.exit(1)

    results = [
        result
        for ticker in config.leaders
        if (result := _analyze_leader(group_dir, ticker, benchmark_dir))
    ]
    if not results:
        print("error: no factor data for any leader.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps([dataclasses.asdict(r) for r in results], indent=2))
    else:
        _print_report(config.name, results)


if __name__ == "__main__":
    main()

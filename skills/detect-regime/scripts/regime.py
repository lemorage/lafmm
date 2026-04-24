#!/usr/bin/env python3
"""Detect market regime for a LAFMM group's leaders.

Thin CLI wrapper around lafmm.quant.regime.

SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lafmm.loader import load_group_config, load_price_series
from lafmm.quant.regime import DEFAULT_MAX_LAG, detect_regime, hurst_exponent, variance_ratio
from lafmm.quant.types import to_returns


@dataclass(frozen=True, slots=True)
class RegimeResult:
    ticker: str
    regime: str
    hurst: float | None
    variance_ratio: float | None
    vr_pvalue: float | None
    bar_count: int


def _analyze_ticker(ticker_dir: Path, max_lag: int) -> RegimeResult | None:
    series = load_price_series(ticker_dir)
    if series is None:
        return None
    returns = to_returns(series)
    hurst = hurst_exponent(returns, max_lag)
    regime = detect_regime(returns, max_lag)
    vr = variance_ratio(returns)
    return RegimeResult(
        ticker=ticker_dir.name.upper(),
        regime=regime,
        hurst=round(hurst, 4) if hurst is not None else None,
        variance_ratio=vr[0] if vr else None,
        vr_pvalue=vr[1] if vr else None,
        bar_count=len(series.close),
    )


def _print_report(group_name: str, results: Sequence[RegimeResult]) -> None:
    print(f"Group: {group_name}")
    print()
    for result in results:
        hurst_display = f"{result.hurst:.4f}" if result.hurst is not None else "N/A"
        print(
            f"  {result.ticker:<6} regime: {result.regime:<15} "
            f"Hurst: {hurst_display}  ({result.bar_count} bars)"
        )
        if result.variance_ratio is not None:
            print(f"         VR: {result.variance_ratio}  p-value: {result.vr_pvalue}")
    print()
    regimes = [result.regime for result in results]
    if len(set(regimes)) == 1:
        print(f"  Leaders agree: {regimes[0]}")
    else:
        print(f"  Leaders disagree: {', '.join(regimes)}. Exercise caution.")


def _resolve_and_analyze(
    group_dir: Path,
    ticker: str,
    max_lag: int,
) -> RegimeResult | None:
    ticker_dir = group_dir / ticker
    if not ticker_dir.is_dir():
        ticker_dir = group_dir / ticker.upper()
    if not ticker_dir.is_dir():
        print(f"  {ticker}: no data directory found", file=sys.stderr)
        return None
    return _analyze_ticker(ticker_dir, max_lag)


def _print_json(group_name: str, results: Sequence[RegimeResult]) -> None:
    output = [dataclasses.asdict(result) for result in results]
    print(json.dumps({"group": group_name, "leaders": output}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect regime for LAFMM group")
    parser.add_argument("group_dir", type=Path, help="path to group directory")
    parser.add_argument("--max-lag", type=int, default=DEFAULT_MAX_LAG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    group_dir = args.group_dir.expanduser().resolve()
    config = load_group_config(group_dir)

    results = [
        result
        for ticker in config.leaders
        if (result := _resolve_and_analyze(group_dir, ticker, args.max_lag)) is not None
    ]

    if not results:
        print("error: no data for any leader. run fetch-prices first.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        _print_json(config.name, results)
    else:
        _print_report(config.name, results)


if __name__ == "__main__":
    main()

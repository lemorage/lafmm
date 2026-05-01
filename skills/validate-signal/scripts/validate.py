#!/usr/bin/env python3
"""Validate Livermore signals for a LAFMM group.

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

from lafmm.loader import load_group, load_group_config, load_price_series
from lafmm.models import GroupState, SignalType
from lafmm.quant.signal import (
    DecayPoint,
    signal_decay,
    signal_hit_rate,
    signal_pvalue,
    signal_sharpe,
)
from lafmm.quant.types import to_returns

DEFAULT_HORIZON = 5
DEFAULT_PERMUTATIONS = 10_000


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ticker: str
    signal_type: str
    signal_count: int
    hit_rate: float
    sharpe: float | None
    pvalue: float | None
    decay: tuple[DecayPoint, ...]


def _resolve_direction(signal_type: SignalType) -> int:
    if signal_type in (SignalType.BUY, SignalType.DANGER_DOWN_OVER):
        return 1
    if signal_type in (SignalType.SELL, SignalType.DANGER_UP_OVER):
        return -1
    return 0


def _validate_ticker(
    group_dir: Path,
    ticker: str,
    signal_type: SignalType,
    horizon: int,
    permutations: int,
) -> ValidationResult | None:
    series = load_price_series(group_dir / ticker)
    if series is None:
        print(f"  {ticker}: no price data", file=sys.stderr)
        return None
    returns = to_returns(series)

    group_state = load_group(group_dir)
    signals = _extract_signal_dates(group_state, ticker, signal_type)
    if not signals:
        return None

    direction = _resolve_direction(signal_type)
    if direction == 0:
        return None

    hit_result = signal_hit_rate(returns, signals, direction, horizon)
    sharpe = signal_sharpe(returns, signals, direction, horizon)
    pvalue = signal_pvalue(returns, signals, direction, horizon, permutations, seed=42)
    decay = signal_decay(returns, signals, direction)

    return ValidationResult(
        ticker=ticker,
        signal_type=signal_type.name,
        signal_count=len(signals),
        hit_rate=hit_result.hit_rate,
        sharpe=sharpe,
        pvalue=pvalue,
        decay=tuple(decay),
    )


def _extract_signal_dates(
    group_state: GroupState,
    ticker: str,
    signal_type: SignalType,
) -> tuple[str, ...]:
    from lafmm.group import group_leaders, group_tracked

    all_stocks = (*group_leaders(group_state), *group_tracked(group_state))
    for stock in all_stocks:
        if stock.ticker.upper() == ticker.upper():
            return tuple(
                signal.date for signal in stock.engine.signals if signal.signal_type == signal_type
            )
    return ()


def _print_report(results: Sequence[ValidationResult], horizon: int) -> None:
    for result in results:
        print(f"  {result.ticker} {result.signal_type} ({result.signal_count} signals)")
        print(f"    Hit rate:  {result.hit_rate:.0%} at {horizon}d horizon")
        sharpe_str = f"{result.sharpe:.2f}" if result.sharpe is not None else "N/A"
        print(f"    Sharpe:    {sharpe_str}")
        pvalue_str = f"{result.pvalue:.4f}" if result.pvalue is not None else "N/A"
        print(f"    p-value:   {pvalue_str}")
        if result.decay:
            decay_str = "  ".join(
                f"{point.horizon}d: {point.mean_return:+.4f}" for point in result.decay
            )
            print(f"    Decay:     {decay_str}")
        print()


def _print_verdict(results: Sequence[ValidationResult]) -> None:
    for result in results:
        if result.pvalue is not None and result.pvalue < 0.05:
            print(f"  {result.ticker} {result.signal_type}: SIGNIFICANT (p={result.pvalue})")
        elif result.pvalue is not None:
            print(f"  {result.ticker} {result.signal_type}: NOT SIGNIFICANT (p={result.pvalue})")
        else:
            print(f"  {result.ticker} {result.signal_type}: INSUFFICIENT DATA")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate signals for LAFMM group")
    parser.add_argument("group_dir", type=Path, help="path to group directory")
    parser.add_argument(
        "--signal",
        default="BUY",
        choices=["BUY", "SELL", "DANGER_UP_OVER", "DANGER_DOWN_OVER"],
    )
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    group_dir = args.group_dir.expanduser().resolve()
    config = load_group_config(group_dir)
    signal_type = SignalType[args.signal]

    results: list[ValidationResult] = []
    for ticker in config.leaders:
        result = _validate_ticker(group_dir, ticker, signal_type, args.horizon, args.permutations)
        if result is not None:
            results.append(result)

    if not results:
        print(f"no {args.signal} signals found for any leader.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps([dataclasses.asdict(r) for r in results], indent=2))
    else:
        print(f"Signal validation: {args.signal} at {args.horizon}d horizon")
        print(f"Group: {config.name}")
        print()
        _print_report(results, args.horizon)
        _print_verdict(results)


if __name__ == "__main__":
    main()

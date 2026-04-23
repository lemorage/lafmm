from __future__ import annotations

import math
from collections.abc import Sequence

from lafmm.quant.types import PriceSeries, Returns

TRADING_DAYS_PER_YEAR = 252


def _true_ranges(series: PriceSeries) -> Sequence[float]:
    if len(series.close) < 2:
        return ()
    return tuple(
        max(
            series.high[i] - series.low[i],
            abs(series.high[i] - series.close[i - 1]),
            abs(series.low[i] - series.close[i - 1]),
        )
        for i in range(1, len(series.close))
    )


def atr(series: PriceSeries, period: int = 14) -> float | None:
    ranges = _true_ranges(series)
    if len(ranges) < period:
        return None
    return sum(ranges[-period:]) / period


def atr_pct(series: PriceSeries, period: int = 14) -> float | None:
    val = atr(series, period)
    if val is None:
        return None
    last_close = series.close[-1]
    if last_close <= 0:
        return None
    return (val / last_close) * 100


def realized_vol(returns: Returns, period: int = 20) -> float | None:
    vals = returns.values[-period:]
    if len(vals) < period:
        return None
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR)

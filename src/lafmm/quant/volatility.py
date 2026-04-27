from __future__ import annotations

import math

from lafmm.indicators import atr as atr_series
from lafmm.quant.types import PriceSeries, Returns, sample_variance

TRADING_DAYS_PER_YEAR = 252


def atr(series: PriceSeries, period: int = 14) -> float | None:
    if len(series.close) < period + 1:
        return None
    values = atr_series(series.high, series.low, series.close, period)
    return values[-1]


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
    return math.sqrt(sample_variance(vals)) * math.sqrt(TRADING_DAYS_PER_YEAR)

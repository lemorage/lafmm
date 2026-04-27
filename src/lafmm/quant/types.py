from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class PriceSeries:
    dates: tuple[str, ...]
    open: tuple[float, ...]
    high: tuple[float, ...]
    low: tuple[float, ...]
    close: tuple[float, ...]
    volume: tuple[int, ...]


def bar_at(series: PriceSeries, index: int) -> Bar:
    return Bar(
        date=series.dates[index],
        open=series.open[index],
        high=series.high[index],
        low=series.low[index],
        close=series.close[index],
        volume=series.volume[index],
    )


def bars_to_series(bars: Sequence[Bar]) -> PriceSeries:
    return PriceSeries(
        dates=tuple(bar.date for bar in bars),
        open=tuple(bar.open for bar in bars),
        high=tuple(bar.high for bar in bars),
        low=tuple(bar.low for bar in bars),
        close=tuple(bar.close for bar in bars),
        volume=tuple(bar.volume for bar in bars),
    )


@dataclass(frozen=True, slots=True)
class Returns:
    dates: tuple[str, ...]
    values: tuple[float, ...]
    log: bool = False


def to_returns(series: PriceSeries, *, log: bool = False) -> Returns:
    if len(series.close) < 2:
        return Returns(dates=(), values=(), log=log)
    closes = series.close
    pairs = [
        (series.dates[i], closes[i], closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    dates = tuple(d for d, _, _ in pairs)
    if log:
        vals = tuple(math.log(c / prev) for _, c, prev in pairs)
    else:
        vals = tuple((c - prev) / prev for _, c, prev in pairs)
    return Returns(dates=dates, values=vals, log=log)


def sample_variance(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / (n - 1)

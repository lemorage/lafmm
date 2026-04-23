from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceSeries:
    dates: tuple[str, ...]
    open: tuple[float, ...]
    high: tuple[float, ...]
    low: tuple[float, ...]
    close: tuple[float, ...]
    volume: tuple[int, ...]


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

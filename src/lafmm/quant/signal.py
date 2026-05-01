from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from lafmm.quant.types import Returns, sample_variance

DEFAULT_PERMUTATIONS = 10_000
DEFAULT_HORIZONS = (1, 5, 10, 20)


@dataclass(frozen=True, slots=True)
class HitRateResult:
    wins: int
    losses: int
    total: int
    hit_rate: float


@dataclass(frozen=True, slots=True)
class DecayPoint:
    horizon: int
    mean_return: float
    count: int


def _build_date_index(returns: Returns) -> dict[str, int]:
    return {d: i for i, d in enumerate(returns.dates)}


def _forward_return(
    values: Sequence[float],
    start: int,
    horizon: int,
) -> float | None:
    end = start + horizon
    if end > len(values):
        return None
    return math.prod(1 + values[i] for i in range(start, end)) - 1


def _gather_forward_returns(
    values: Sequence[float],
    date_index: Mapping[str, int],
    signal_dates: Sequence[str],
    direction: int,
    horizon: int,
) -> tuple[float, ...]:
    results: list[float] = []
    for date in signal_dates:
        if date not in date_index:
            continue
        forward_return = _forward_return(values, date_index[date], horizon)
        if forward_return is not None:
            results.append(forward_return * direction)
    return tuple(results)


def signal_hit_rate(
    returns: Returns,
    signal_dates: Sequence[str],
    direction: int,
    horizon: int = 5,
) -> HitRateResult:
    forward_returns = _gather_forward_returns(
        returns.values,
        _build_date_index(returns),
        signal_dates,
        direction,
        horizon,
    )
    wins = sum(1 for r in forward_returns if r > 0)
    losses = len(forward_returns) - wins
    total = wins + losses
    rate = wins / total if total > 0 else 0.0
    return HitRateResult(wins=wins, losses=losses, total=total, hit_rate=round(rate, 4))


def signal_decay(
    returns: Returns,
    signal_dates: Sequence[str],
    direction: int = 1,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> Sequence[DecayPoint]:
    date_index = _build_date_index(returns)
    return tuple(
        _decay_point(returns.values, date_index, signal_dates, direction, horizon)
        for horizon in horizons
    )


def _decay_point(
    values: Sequence[float],
    date_index: Mapping[str, int],
    signal_dates: Sequence[str],
    direction: int,
    horizon: int,
) -> DecayPoint:
    forward_returns = _gather_forward_returns(values, date_index, signal_dates, direction, horizon)
    mean = sum(forward_returns) / len(forward_returns) if forward_returns else 0.0
    return DecayPoint(horizon=horizon, mean_return=round(mean, 6), count=len(forward_returns))


def signal_sharpe(
    returns: Returns,
    signal_dates: Sequence[str],
    direction: int = 1,
    horizon: int = 5,
) -> float | None:
    forward_returns = _gather_forward_returns(
        returns.values,
        _build_date_index(returns),
        signal_dates,
        direction,
        horizon,
    )
    if len(forward_returns) < 3:
        return None
    mean = sum(forward_returns) / len(forward_returns)
    var = sample_variance(forward_returns)
    if var <= 0:
        return None
    return round(mean / math.sqrt(var), 4)


def signal_pvalue(
    returns: Returns,
    signal_dates: Sequence[str],
    direction: int = 1,
    horizon: int = 5,
    permutations: int = DEFAULT_PERMUTATIONS,
    seed: int | None = None,
) -> float | None:
    date_index = _build_date_index(returns)
    valid_dates = [d for d in signal_dates if d in date_index]
    if len(valid_dates) < 3:
        return None
    observed = _mean_forward(returns.values, date_index, valid_dates, direction, horizon)
    if observed is None:
        return None
    rng = random.Random(seed)
    all_dates = list(returns.dates)
    count_exceeding = 0
    for _ in range(permutations):
        shuffled_dates = rng.sample(all_dates, len(valid_dates))
        permuted_mean = _mean_forward(
            returns.values,
            date_index,
            shuffled_dates,
            direction,
            horizon,
        )
        if permuted_mean is not None and permuted_mean >= observed:
            count_exceeding += 1
    return round(count_exceeding / permutations, 4)


def _mean_forward(
    values: Sequence[float],
    date_index: Mapping[str, int],
    dates: Sequence[str],
    direction: int,
    horizon: int,
) -> float | None:
    forward_returns = _gather_forward_returns(values, date_index, dates, direction, horizon)
    if not forward_returns:
        return None
    return sum(forward_returns) / len(forward_returns)

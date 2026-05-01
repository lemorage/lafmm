from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from lafmm.quant.types import Returns

MIN_RETURNS_FOR_SIMULATION = 10


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    depth: float
    start_date: str
    end_date: str


def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    if win_loss_ratio <= 0:
        return 0.0
    return (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio


def half_kelly(win_rate: float, win_loss_ratio: float) -> float:
    return kelly_fraction(win_rate, win_loss_ratio) / 2


def position_size(
    capital: float,
    sharpe: float,
    volatility: float,
    max_risk_percent: float = 2.0,
) -> float:
    if volatility <= 0 or capital <= 0:
        return 0.0
    volatility_adjusted_size = capital * sharpe / volatility
    max_risk_dollars = capital * max_risk_percent / 100
    return min(volatility_adjusted_size, max_risk_dollars)


def max_drawdown(returns: Returns) -> DrawdownResult | None:
    if len(returns.values) < 2:
        return None
    equity = _build_equity_curve(returns.values)
    result = _worst_drawdown(equity, returns.dates)
    if result is None or result.depth == 0:
        return None
    return result


def _max_drawdown_depth(equity: Sequence[float]) -> float:
    peak = equity[0]
    worst = 0.0
    for value in equity[1:]:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0
        if drawdown > worst:
            worst = drawdown
    return round(worst, 4)


def _worst_drawdown(
    equity: Sequence[float],
    dates: Sequence[str],
) -> DrawdownResult | None:
    peak = equity[0]
    worst = 0.0
    peak_date = dates[0]
    drawdown_start = peak_date
    drawdown_end = peak_date
    for i in range(1, len(equity)):
        if equity[i] > peak:
            peak = equity[i]
            peak_date = dates[i]
        drawdown = (peak - equity[i]) / peak
        if drawdown > worst:
            worst = drawdown
            drawdown_start = peak_date
            drawdown_end = dates[i]
    return DrawdownResult(depth=round(worst, 4), start_date=drawdown_start, end_date=drawdown_end)


def monte_carlo_drawdown(
    returns: Returns,
    simulations: int = 1000,
    horizon: int = 252,
    seed: int | None = None,
) -> Sequence[float]:
    if len(returns.values) < MIN_RETURNS_FOR_SIMULATION:
        return ()
    rng = random.Random(seed)
    values = list(returns.values)
    drawdowns = sorted(_simulate_max_drawdown(rng, values, horizon) for _ in range(simulations))
    return tuple(drawdowns)


def _simulate_max_drawdown(
    rng: random.Random,
    values: Sequence[float],
    horizon: int,
) -> float:
    simulated_returns = rng.choices(values, k=horizon)
    equity = _build_equity_curve(simulated_returns)
    return _max_drawdown_depth(equity)


def drawdown_percentile(drawdowns: Sequence[float], percentile: float = 95) -> float:
    if not drawdowns:
        return 0.0
    index = int(len(drawdowns) * percentile / 100)
    return drawdowns[min(index, len(drawdowns) - 1)]


def portfolio_heat(
    sizes: Sequence[float],
    correlations: Mapping[tuple[int, int], float],
) -> float:
    position_count = len(sizes)
    if position_count == 0:
        return 0.0
    portfolio_variance = 0.0
    for i in range(position_count):
        for j in range(position_count):
            if i == j:
                portfolio_variance += sizes[i] ** 2
            else:
                correlation = correlations.get((i, j), correlations.get((j, i), 0.0))
                portfolio_variance += sizes[i] * sizes[j] * correlation
    return math.sqrt(max(portfolio_variance, 0))


def _build_equity_curve(returns: Sequence[float]) -> tuple[float, ...]:
    equity = [1.0]
    for daily_return in returns:
        equity.append(equity[-1] * (1 + daily_return))
    return tuple(equity)

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from lafmm.quant.types import Returns, sample_variance

TRADING_DAYS_PER_YEAR = 252
MIN_OVERLAPPING_DATES = 10
SINGULARITY_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class FactorResult:
    alpha: float
    alpha_tstat: float
    betas: tuple[float, ...]
    r_squared: float


def factor_regression(
    strategy: Returns,
    market: Returns,
    factors: Sequence[Returns] = (),
) -> FactorResult | None:
    all_factors = (market, *factors)
    aligned = _align_multi(strategy, all_factors)
    if aligned is None:
        return None
    _dates, y, xs = aligned
    if len(y) < len(xs) + 3:
        return None
    return _ols(y, xs)


def rolling_alpha(
    strategy: Returns,
    market: Returns,
    factors: Sequence[Returns] = (),
    window: int = 60,
) -> Sequence[tuple[str, float]]:
    return _rolling_ols(strategy, (market, *factors), window, lambda r: r.alpha)


def rolling_beta(
    strategy: Returns,
    market: Returns,
    window: int = 60,
) -> Sequence[tuple[str, float]]:
    return _rolling_ols(
        strategy,
        (market,),
        window,
        lambda r: r.betas[0] if r.betas else None,
    )


def _rolling_ols(
    strategy: Returns,
    factors: Sequence[Returns],
    window: int,
    extract: Callable[[FactorResult], float | None],
) -> tuple[tuple[str, float], ...]:
    aligned = _align_multi(strategy, factors)
    if aligned is None:
        return ()
    dates, y, xs = aligned
    results: list[tuple[str, float]] = []
    for end in range(window, len(y) + 1):
        start = end - window
        chunk_xs = tuple(col[start:end] for col in xs)
        result = _ols(y[start:end], chunk_xs)
        if result is not None:
            value = extract(result)
            if value is not None:
                results.append((dates[end - 1], value))
    return tuple(results)


def _align_multi(
    strategy: Returns,
    factors: Sequence[Returns],
) -> tuple[tuple[str, ...], Sequence[float], tuple[Sequence[float], ...]] | None:
    common = set(strategy.dates)
    for factor in factors:
        common &= set(factor.dates)
    dates = tuple(sorted(common))
    if len(dates) < MIN_OVERLAPPING_DATES:
        return None
    strategy_index = {date: i for i, date in enumerate(strategy.dates)}
    y = tuple(strategy.values[strategy_index[date]] for date in dates)
    factor_index_maps = [{date: i for i, date in enumerate(factor.dates)} for factor in factors]
    xs = tuple(
        tuple(factor.values[index[date]] for date in dates)
        for factor, index in zip(factors, factor_index_maps, strict=True)
    )
    return dates, y, xs


def _ols(
    y: Sequence[float],
    xs: tuple[Sequence[float], ...],
) -> FactorResult | None:
    n = len(y)
    k = len(xs)
    if n < k + 3:
        return None
    mean_y = sum(y) / n
    mean_xs = tuple(sum(col) / n for col in xs)
    betas = _compute_betas(y, xs, mean_y, mean_xs, n, k)
    if betas is None:
        return None
    alpha = mean_y - sum(betas[j] * mean_xs[j] for j in range(k))
    return _build_result(y, xs, alpha, betas, mean_y, n, k)


def _r_squared(
    y: Sequence[float],
    residuals: Sequence[float],
    mean_y: float,
) -> float:
    ss_res = sum(r * r for r in residuals)
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0.0


def _build_result(
    y: Sequence[float],
    xs: tuple[Sequence[float], ...],
    alpha: float,
    betas: tuple[float, ...],
    mean_y: float,
    n: int,
    k: int,
) -> FactorResult:
    residuals = tuple(y[i] - alpha - sum(betas[j] * xs[j][i] for j in range(k)) for i in range(n))
    alpha_se = _alpha_standard_error(residuals, n, k)
    alpha_tstat = alpha / alpha_se if alpha_se > 0 else 0.0
    annualized_alpha = alpha * TRADING_DAYS_PER_YEAR
    return FactorResult(
        alpha=round(annualized_alpha, 6),
        alpha_tstat=round(alpha_tstat, 4),
        betas=tuple(round(b, 4) for b in betas),
        r_squared=round(_r_squared(y, residuals, mean_y), 4),
    )


def _compute_betas(
    y: Sequence[float],
    xs: tuple[Sequence[float], ...],
    mean_y: float,
    mean_xs: tuple[float, ...],
    n: int,
    k: int,
) -> tuple[float, ...] | None:
    if k == 1:
        return _single_factor_beta(y, xs[0], mean_y, mean_xs[0], n)
    xty = tuple(sum((xs[j][i] - mean_xs[j]) * (y[i] - mean_y) for i in range(n)) for j in range(k))
    xtx = tuple(
        tuple(
            sum((xs[j][i] - mean_xs[j]) * (xs[m][i] - mean_xs[m]) for i in range(n))
            for m in range(k)
        )
        for j in range(k)
    )
    return _solve_2x2(xtx, xty) if k == 2 else _solve_diagonal(xtx, xty, k)


def _single_factor_beta(
    y: Sequence[float],
    x: Sequence[float],
    mean_y: float,
    mean_x: float,
    n: int,
) -> tuple[float, ...] | None:
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
    var = sample_variance(x)
    if var <= 0:
        return None
    return (cov / var,)


def _solve_2x2(
    xtx: tuple[tuple[float, ...], ...],
    xty: tuple[float, ...],
) -> tuple[float, ...] | None:
    det = xtx[0][0] * xtx[1][1] - xtx[0][1] * xtx[1][0]
    if abs(det) < SINGULARITY_TOLERANCE:
        return None
    b0 = (xtx[1][1] * xty[0] - xtx[0][1] * xty[1]) / det
    b1 = (xtx[0][0] * xty[1] - xtx[1][0] * xty[0]) / det
    return (b0, b1)


def _solve_diagonal(
    xtx: tuple[tuple[float, ...], ...],
    xty: tuple[float, ...],
    k: int,
) -> tuple[float, ...] | None:
    for j in range(k):
        if xtx[j][j] == 0:
            return None
    return tuple(xty[j] / xtx[j][j] for j in range(k))


def _alpha_standard_error(
    residuals: Sequence[float],
    n: int,
    k: int,
) -> float:
    if n <= k + 1:
        return 0.0
    mse = sum(r * r for r in residuals) / (n - k - 1)
    return math.sqrt(mse / n)

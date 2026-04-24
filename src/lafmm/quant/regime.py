from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from lafmm.quant.types import Returns, sample_variance

type Regime = Literal["trending", "mean_reverting", "random"]

DEFAULT_MAX_LAG = 20
HURST_TRENDING_THRESHOLD = 0.55
HURST_MEAN_REVERTING_THRESHOLD = 0.45


def hurst_exponent(returns: Returns, max_lag: int = DEFAULT_MAX_LAG) -> float | None:
    values = returns.values
    if len(values) < max_lag * 2:
        return None
    log_lags: list[float] = []
    log_rs: list[float] = []
    for lag in range(2, max_lag + 1):
        rs = _rescaled_range(values, lag)
        if rs is not None and rs > 0:
            log_lags.append(math.log(lag))
            log_rs.append(math.log(rs))
    if len(log_lags) < 3:
        return None
    return _slope(log_lags, log_rs)


def detect_regime(returns: Returns, max_lag: int = DEFAULT_MAX_LAG) -> Regime:
    hurst = hurst_exponent(returns, max_lag)
    if hurst is None:
        return "random"
    if hurst > HURST_TRENDING_THRESHOLD:
        return "trending"
    if hurst < HURST_MEAN_REVERTING_THRESHOLD:
        return "mean_reverting"
    return "random"


def variance_ratio(returns: Returns, period: int = 5) -> tuple[float, float] | None:
    values = returns.values
    n = len(values)
    if n < period * 3:
        return None
    single_var = sample_variance(values)
    chunked = _sum_chunks(values, period)
    multi_var = sample_variance(chunked) / period
    if single_var == 0:
        return None
    vr = multi_var / single_var
    z_stat = (vr - 1) * math.sqrt(n)
    p_value = 2 * (1 - _normal_cdf(abs(z_stat)))
    return round(vr, 4), round(p_value, 4)


def _rescaled_range(values: Sequence[float], lag: int) -> float | None:
    rs_values: list[float] = []
    for start in range(0, len(values) - lag + 1, lag):
        chunk = values[start : start + lag]
        if len(chunk) < lag:
            break
        rs = _chunk_rs(chunk, lag)
        if rs is not None:
            rs_values.append(rs)
    if not rs_values:
        return None
    return sum(rs_values) / len(rs_values)


def _chunk_rs(chunk: Sequence[float], lag: int) -> float | None:
    mean = sum(chunk) / lag
    deviations = [v - mean for v in chunk]
    cumulative: list[float] = []
    running = 0.0
    for d in deviations:
        running += d
        cumulative.append(running)
    r = max(cumulative) - min(cumulative)
    s = math.sqrt(sum(d * d for d in deviations) / lag)
    if s <= 0:
        return None
    return r / s


def _slope(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_xx = sum(v * v for v in x)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.5
    return (n * sum_xy - sum_x * sum_y) / denom


def _sum_chunks(values: Sequence[float], size: int) -> tuple[float, ...]:
    return tuple(sum(values[i : i + size]) for i in range(0, len(values) - size + 1, size))


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

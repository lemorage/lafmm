from __future__ import annotations

import math
from collections.abc import Sequence

from lafmm.quant.types import Returns

_EPSILON = 1e-12


def _align_returns(
    a: Returns,
    b: Returns,
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[float, ...]]:
    common = sorted(set(a.dates) & set(b.dates))
    if not common:
        return (), (), ()
    idx_a = {d: i for i, d in enumerate(a.dates)}
    idx_b = {d: i for i, d in enumerate(b.dates)}
    vals_a = tuple(a.values[idx_a[d]] for d in common)
    vals_b = tuple(b.values[idx_b[d]] for d in common)
    return tuple(common), vals_a, vals_b


def _pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
    var_x = sum((v - mean_x) ** 2 for v in x) / (n - 1)
    var_y = sum((v - mean_y) ** 2 for v in y) / (n - 1)
    denom = math.sqrt(var_x) * math.sqrt(var_y)
    if denom < _EPSILON:
        return None
    return cov / denom


def pairwise_correlation(a: Returns, b: Returns) -> float | None:
    _, vals_a, vals_b = _align_returns(a, b)
    return _pearson(vals_a, vals_b)


def rolling_correlation(
    a: Returns,
    b: Returns,
    window: int = 30,
) -> Sequence[tuple[str, float]]:
    common, vals_a, vals_b = _align_returns(a, b)
    if len(vals_a) < window:
        return ()
    results: list[tuple[str, float]] = []
    for i in range(window, len(vals_a) + 1):
        r = _pearson(vals_a[i - window : i], vals_b[i - window : i])
        if r is not None:
            results.append((common[i - 1], round(r, 4)))
    return tuple(results)

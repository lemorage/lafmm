"""Technical indicators: pure math on price sequences."""

from __future__ import annotations

from collections.abc import Sequence


def sma(values: Sequence[float], period: int) -> list[float]:
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        result.append(sum(values[start : i + 1]) / (i - start + 1))
    return result


def ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float]:
    if len(values) < 2:
        return [50.0] * len(values)
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    return [50.0, *_rsi_from_deltas(deltas, period)]


def _rsi_from_deltas(deltas: Sequence[float], period: int) -> list[float]:
    avg_gain = avg_loss = 0.0
    result: list[float] = []

    for i, d in enumerate(deltas):
        if i < period:
            avg_gain += max(0, d) / period
            avg_loss += max(0, -d) / period
            result.append(50.0)
            continue
        avg_gain = (avg_gain * (period - 1) + max(0, d)) / period
        avg_loss = (avg_loss * (period - 1) + max(0, -d)) / period
        if avg_loss == 0:
            result.append(100.0 if avg_gain > 0 else 50.0)
        else:
            result.append(100.0 - 100.0 / (1.0 + avg_gain / avg_loss))

    return result


def bollinger(
    values: Sequence[float],
    period: int = 20,
    width: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    mid = sma(values, period)
    upper: list[float] = []
    lower: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        mean = mid[i]
        var = sum((v - mean) ** 2 for v in window) / len(window)
        std = var**0.5
        upper.append(mean + width * std)
        lower.append(mean - width * std)
    return mid, upper, lower


def macd(
    values: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema, strict=True)]
    signal_line = ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line, strict=True)]
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------


def stochastic(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[list[float], list[float]]:
    n = len(closes)
    k_line: list[float] = []
    for i in range(n):
        start = max(0, i - k_period + 1)
        hh = max(highs[start : i + 1])
        ll = min(lows[start : i + 1])
        k_line.append((closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50.0)
    d_line = sma(k_line, d_period)
    return k_line, d_line


def williams_r(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float]:
    n = len(closes)
    result: list[float] = []
    for i in range(n):
        start = max(0, i - period + 1)
        hh = max(highs[start : i + 1])
        ll = min(lows[start : i + 1])
        result.append((hh - closes[i]) / (hh - ll) * -100 if hh != ll else -50.0)
    return result


def cci(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 20,
) -> list[float]:
    typical = [(h + lo + c) / 3 for h, lo, c in zip(highs, lows, closes, strict=True)]
    tp_sma = sma(typical, period)
    result: list[float] = []
    for i in range(len(typical)):
        start = max(0, i - period + 1)
        window = typical[start : i + 1]
        mean_dev = sum(abs(v - tp_sma[i]) for v in window) / len(window)
        result.append((typical[i] - tp_sma[i]) / (0.015 * mean_dev) if mean_dev else 0.0)
    return result


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def rma(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    k = 1 / period
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def dema(values: Sequence[float], period: int) -> list[float]:
    e1 = ema(values, period)
    e2 = ema(e1, period)
    return [2 * a - b for a, b in zip(e1, e2, strict=True)]


def tema(values: Sequence[float], period: int) -> list[float]:
    e1 = ema(values, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return [3 * a - 3 * b + c for a, b, c in zip(e1, e2, e3, strict=True)]


def zscore(values: Sequence[float], period: int = 20) -> list[float]:
    means = sma(values, period)
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        if len(window) < 2:
            result.append(0.0)
            continue
        mean = means[i]
        variance = sum((v - mean) ** 2 for v in window) / (len(window) - 1)
        std = variance**0.5
        result.append((values[i] - mean) / std if std > 0 else 0.0)
    return result


def true_range(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> list[float]:
    ranges = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        ranges.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    return ranges


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float]:
    return rma(true_range(highs, lows, closes), period)


def adx(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float]:
    n = len(closes)
    if n < 2:
        return [0.0] * n
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    tr = true_range(highs, lows, closes)
    smooth_tr = rma(tr, period)
    smooth_plus = rma(plus_dm, period)
    smooth_minus = rma(minus_dm, period)
    dx: list[float] = []
    for st, sp, sm in zip(smooth_tr, smooth_plus, smooth_minus, strict=True):
        plus_di = sp / st * 100 if st else 0.0
        minus_di = sm / st * 100 if st else 0.0
        total = plus_di + minus_di
        dx.append(abs(plus_di - minus_di) / total * 100 if total else 0.0)
    return rma(dx, period)


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


def obv(closes: Sequence[float], volumes: Sequence[float]) -> list[float]:
    if not closes:
        return []
    result = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


def vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
) -> list[float]:
    cum_vol = 0.0
    cum_tp_vol = 0.0
    result: list[float] = []
    for h, lo, c, v in zip(highs, lows, closes, volumes, strict=True):
        cum_vol += v
        cum_tp_vol += (h + lo + c) / 3 * v
        result.append(cum_tp_vol / cum_vol if cum_vol else c)
    return result


def relative_volume(
    volumes: Sequence[float],
    period: int = 20,
) -> list[float]:
    avg = sma(volumes, period)
    return [v / a if a else 1.0 for v, a in zip(volumes, avg, strict=True)]

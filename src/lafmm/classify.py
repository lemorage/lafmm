"""Trade genome classification: 4-axis type codes for every trade."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from lafmm.indicators import relative_volume, rsi, sma, zscore

type Trend = Literal["W", "N", "A"]
type Cadence = Literal["F", "S", "P"]
type Setup = Literal["B", "K", "R"]
type VolumeConfirm = Literal["C", "U"]
type Regime = Literal["BULL", "STRESS", "COMPLACENT", "BEAR", "CHOP", "PANIC"]
type Side = Literal["long", "short"]


@dataclass(frozen=True, slots=True)
class ClassifyConfig:
    trend_sma: tuple[int, int, int] = (50, 150, 200)
    cadence_swing_max_days: int = 20
    breakout_lookback: int = 50
    breakout_proximity_pct: float = 1.0
    reversal_proximity_pct: float = 5.0
    reversal_rsi: float = 30.0
    volume_threshold: float = 1.4
    regime_vix_zscore_lookback: int = 60
    regime_vix_zscore_high: float = 1.5
    regime_vix_zscore_low: float = -1.0
    regime_backwardation_threshold: float = 1.05


DEFAULT_CONFIG = ClassifyConfig()


@dataclass(frozen=True, slots=True)
class Snapshot:
    close: float
    sma_fast: float
    sma_mid: float
    sma_slow: float
    rsi_14: float
    high_lookback: float
    low_lookback: float
    volume_ratio: float
    hold_days: int
    side: Side


@dataclass(frozen=True, slots=True)
class TradeGenome:
    trend: Trend
    cadence: Cadence
    setup: Setup
    volume: VolumeConfirm
    side: Side
    hold_days: int

    @property
    def code(self) -> str:
        return f"{self.trend}-{self.cadence}-{self.setup}-{self.volume}"


# ── Axis classifiers ──────────────────────────────────────────────


def _market_trend(snapshot: Snapshot) -> Trend:
    if snapshot.close > snapshot.sma_fast > snapshot.sma_mid > snapshot.sma_slow:
        return "W"
    if snapshot.close < snapshot.sma_slow:
        return "A"
    if snapshot.sma_fast < snapshot.sma_mid < snapshot.sma_slow:
        return "A"
    return "N"


def _classify_trend(snapshot: Snapshot) -> Trend:
    trend = _market_trend(snapshot)
    if snapshot.side == "short" and trend != "N":
        return "A" if trend == "W" else "W"
    return trend


def _classify_cadence(hold_days: int, swing_max: int) -> Cadence:
    if hold_days < 1:
        return "F"
    if hold_days <= swing_max:
        return "S"
    return "P"


def _classify_setup(snapshot: Snapshot, config: ClassifyConfig) -> Setup:
    breakout_pct = config.breakout_proximity_pct / 100
    reversal_pct = config.reversal_proximity_pct / 100
    if snapshot.close >= snapshot.high_lookback * (1 - breakout_pct):
        return "B"
    if snapshot.close <= snapshot.low_lookback * (1 + reversal_pct):
        return "R"
    if snapshot.rsi_14 < config.reversal_rsi:
        return "R"
    return "K"


def _classify_volume(volume_ratio: float, threshold: float) -> VolumeConfirm:
    return "C" if volume_ratio > threshold else "U"


# ── Public API ─────────────────────────────────────────────────────


def enrich(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    entry_idx: int,
    hold_days: int,
    side: Side,
    config: ClassifyConfig = DEFAULT_CONFIG,
) -> Snapshot:
    fast, mid, slow = config.trend_sma
    lookback_start = max(0, entry_idx - config.breakout_lookback + 1)
    return Snapshot(
        close=closes[entry_idx],
        sma_fast=sma(closes, fast)[entry_idx],
        sma_mid=sma(closes, mid)[entry_idx],
        sma_slow=sma(closes, slow)[entry_idx],
        rsi_14=rsi(closes, 14)[entry_idx],
        high_lookback=max(highs[lookback_start : entry_idx + 1]),
        low_lookback=min(lows[lookback_start : entry_idx + 1]),
        volume_ratio=relative_volume(volumes, 50)[entry_idx],
        hold_days=hold_days,
        side=side,
    )


def classify(
    snapshot: Snapshot,
    config: ClassifyConfig = DEFAULT_CONFIG,
) -> TradeGenome:
    return TradeGenome(
        trend=_classify_trend(snapshot),
        cadence=_classify_cadence(snapshot.hold_days, config.cadence_swing_max_days),
        setup=_classify_setup(snapshot, config),
        volume=_classify_volume(snapshot.volume_ratio, config.volume_threshold),
        side=snapshot.side,
        hold_days=snapshot.hold_days,
    )


def classify_trade(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    entry_idx: int,
    hold_days: int,
    side: Side,
    config: ClassifyConfig = DEFAULT_CONFIG,
) -> TradeGenome:
    snapshot = enrich(highs, lows, closes, volumes, entry_idx, hold_days, side, config)
    return classify(snapshot, config)


def _spy_trend(
    spy_closes: Sequence[float],
    entry_idx: int,
) -> Literal["bull", "bear", "chop"]:
    sma_50 = sma(spy_closes, 50)[entry_idx]
    sma_200 = sma(spy_closes, 200)[entry_idx]
    close = spy_closes[entry_idx]
    if close > sma_50 > sma_200:
        return "bull"
    if close < sma_50 < sma_200:
        return "bear"
    return "chop"


def _vix_state(
    vix_closes: Sequence[float],
    entry_idx: int,
    config: ClassifyConfig,
    vix3m_closes: Sequence[float] | None = None,
) -> Literal["high", "low", "normal", "panic"]:
    if vix3m_closes is not None and entry_idx < len(vix3m_closes):
        ratio = vix_closes[entry_idx] / vix3m_closes[entry_idx]
        if ratio > config.regime_backwardation_threshold:
            return "panic"
    log_vix = [math.log(v) if v > 0 else 0.0 for v in vix_closes]
    z = zscore(log_vix, config.regime_vix_zscore_lookback)[entry_idx]
    if z > config.regime_vix_zscore_high:
        return "high"
    if z < config.regime_vix_zscore_low:
        return "low"
    return "normal"


def market_regime(
    spy_closes: Sequence[float],
    spy_idx: int,
    vix_closes: Sequence[float] | None = None,
    vix_idx: int | None = None,
    vix3m_closes: Sequence[float] | None = None,
    config: ClassifyConfig = DEFAULT_CONFIG,
) -> Regime:
    if vix_closes is not None and vix_idx is not None:
        vol = _vix_state(vix_closes, vix_idx, config, vix3m_closes)
        if vol == "panic":
            return "PANIC"
    else:
        vol = "normal"

    trend = _spy_trend(spy_closes, spy_idx)
    if trend == "chop":
        return "CHOP"
    if trend == "bull":
        return "STRESS" if vol == "high" else "BULL"
    return "BEAR" if vol == "high" else "COMPLACENT"

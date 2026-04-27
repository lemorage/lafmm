"""Trade genome classification: 4-axis type codes for every trade."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from lafmm.indicators import relative_volume, rsi, sma

type Trend = Literal["W", "N", "A"]
type Cadence = Literal["F", "S", "P"]
type Setup = Literal["B", "K", "R"]
type VolumeConfirm = Literal["C", "U"]
type Regime = Literal["BULL", "CHOP", "BEAR", "PANIC"]
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


def market_regime(
    index_closes: Sequence[float],
    entry_idx: int,
    vix: float | None = None,
) -> Regime:
    if vix is not None and vix >= 35:
        return "PANIC"
    close = index_closes[entry_idx]
    sma_50 = sma(index_closes, 50)[entry_idx]
    sma_200 = sma(index_closes, 200)[entry_idx]
    if close > sma_50 > sma_200:
        return "BULL"
    if close < sma_50 < sma_200:
        return "BEAR"
    return "CHOP"

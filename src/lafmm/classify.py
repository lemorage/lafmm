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
type Regime = Literal["RISK_ON", "RISK_OFF"]
type Side = Literal["long", "short"]

BACKWARDATION_THRESHOLD = 1.10
PANIC_CONFIRM_DAYS = 7
PANIC_EXIT_DAYS = 2


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


def compute_regime_series(
    vix_closes: Sequence[float],
    vix_dates: Sequence[str],
    vix3m_closes: Sequence[float],
    vix3m_dates: Sequence[str],
) -> dict[str, Regime]:
    vix3m_by_date = dict(zip(vix3m_dates, range(len(vix3m_dates)), strict=False))
    current: Regime = "RISK_ON"
    entry_streak = 0
    exit_streak = 0
    result: dict[str, Regime] = {}

    for i, date in enumerate(vix_dates):
        v3i = vix3m_by_date.get(date)
        is_backwardation = False
        if v3i is not None and vix3m_closes[v3i] > 0:
            is_backwardation = vix_closes[i] / vix3m_closes[v3i] > BACKWARDATION_THRESHOLD

        if current == "RISK_OFF":
            if not is_backwardation:
                exit_streak += 1
            else:
                exit_streak = 0
            if exit_streak >= PANIC_EXIT_DAYS:
                current = "RISK_ON"
                entry_streak = 0
                exit_streak = 0
        else:
            exit_streak = 0
            if is_backwardation:
                entry_streak += 1
            else:
                entry_streak = 0
            if entry_streak >= PANIC_CONFIRM_DAYS:
                current = "RISK_OFF"

        result[date] = current

    return result

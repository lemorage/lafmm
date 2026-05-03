# Range Trading

Buys at established support, sells at resistance within a horizontal
range. Only applicable when the stock is NOT in a clear trend.

## Prerequisite

Momentum trend template must score < 6/8 OR SMA 50 must be visually
flat. If the stock is in a confirmed uptrend (≥ 6/8 with all MAs
sloping up), this perspective does not apply — output "NO_RANGE: stock
is in clear uptrend, use Momentum perspective."

## Range Identification (all must be true)

- Price has bounced off a clear support level at least 2 times
- Price has been rejected at a clear resistance level at least 2 times
- Range has existed for at least 3 weeks
- Range width = (Resistance - Support) / Support × 100 must be ≥ 8%
- SMA 50 is flat or nearly flat (not clearly sloping)
- Bollinger Bands are roughly horizontal and not expanding

## Current Position Within Range

```
Range_Position = (Price - Support) / (Resistance - Support) × 100
```

| Position | Zone | Implication |
|----------|------|-------------|
| 0-20% | AT_SUPPORT | Potential buy zone |
| 20-40% | LOWER_HALF | Neutral-bullish within range |
| 40-60% | MIDDLE | No edge — stay out |
| 60-80% | UPPER_HALF | Neutral-bearish within range |
| 80-100% | AT_RESISTANCE | Do not buy |

## Entry Signals (need ≥ 3 of 5)

1. Price within 3% of support level
2. RSI < 40 (oversold within range — tighter threshold than trending)
3. Price at or near Bollinger Band lower band
4. Bullish K-line pattern at support (hammer, bullish engulfing,
   morning star)
5. Volume pattern at support: declining volume as price approaches
   support (selling exhaustion) followed by volume increase on the
   bounce candle(s) (buyers stepping in). Both halves should be
   visible for full credit.

## Trade Parameters (if entry warranted)

- **Stop loss**: Support minus 1.5-2% (or 1 × ATR below support)
- **Target 1**: 70% of range width above support (conservative)
- **Target 2**: Resistance minus 2-3% (full range target)
- **Risk:Reward**: Must be at least 1.5:1
- **Position size**: Same 2% risk calculation as momentum, using range
  stop distance

## Indicator Usage in Range Context

- **Bollinger Bands**: Flat, non-expanding bands confirm range. Price
  touching lower band = buy signal support.
- **RSI**: Tighter thresholds: < 40 = oversold buy, > 60 = overbought
  sell (not the 30/70 of trending markets).
- **Volume**: Higher at support bounces, lower in mid-range drift.
  Spike at support = institutional buying.
- **SMA 50**: Must be flat. Rising → use Momentum. Falling → Avoid.
- **ATR**: Use for stop calculation. Stop = Support - (1 to 1.5 × ATR).
- **EMA 21**: Less relevant in range context.

## Invalidation

- Price breaks below support with above-average volume → RANGE BROKEN
  DOWN → stop out → AVOID
- Price breaks above resistance with above-average volume → RANGE
  BROKEN UP → switch to Momentum for breakout evaluation
- Range narrows below 5% width → no longer tradeable

## Verdicts

**RANGE_BUY**: Valid range, price at support, ≥ 3 entry signals, R:R ≥ 1.5:1.

**RANGE_WATCH_SUPPORT**: Valid range, price not yet at support. Set alert.

**RANGE_WATCH_RESISTANCE**: At resistance — if holding, consider selling.

**RANGE_EXISTS_NO_EDGE**: Range identified but price in middle (40-60%).

**NO_RANGE**: Stock is trending or no clear support/resistance pattern.

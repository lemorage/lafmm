---
name: chart
description: >
  Render braille terminal charts for any tracked stock — price action,
  candlesticks, and 11 technical indicators. Use this skill whenever the
  user mentions charts, plots, graphs, candlesticks, K-lines, MACD, RSI,
  Bollinger Bands, or any indicator visualization. Also use it proactively
  when discussing price trends, after fetching new prices, when the user
  asks "what does X look like" or "what happened to X", or when a visual
  would strengthen your analysis. The chart is a view — it reads data,
  never modifies it.
---

# Chart

Visualize price action and technical indicators for any tracked stock.
Output is braille ANSI — high resolution in the terminal, no GUI needed.

## When to render a chart

- User asks to see a stock's price, trend, or indicator
- You're discussing a signal from cache/ and a visual would clarify
- After daily-update completes and the user is in a review flow
- User says "show me", "plot", "graph", "chart", "candlestick", "K-line"
- You want to confirm an observation ("RSI is elevated" — show it)

## Command

```bash
lafmm chart <type> <ticker> [options]
```

Ticker is auto-resolved across all groups. Use `--group` only to
disambiguate if the same ticker appears in multiple groups.

## Chart types

Pick the type that matches what the user needs to understand.

| Type | What it shows | When to use |
|------|--------------|-------------|
| `line` | Close price | Quick trend check, simplest view |
| `candle` | OHLC candles | Price action detail, wicks show range |
| `overlay` | Close + moving averages | Trend direction, support/resistance |
| `macd` | Price + MACD/Signal/Histogram | Momentum shifts, crossovers |
| `rsi` | Price + RSI (0-100) | Overbought/oversold, divergence |
| `bollinger` | Price + Bollinger Bands | Volatility, squeeze/expansion |
| `stochastic` | Price + %K/%D | Short-term momentum, OB/OS zones |
| `adx` | Price + ADX | Trend strength (>25 = trending) |
| `williams-r` | Price + Williams %R | OB/OS, similar to stochastic |
| `cci` | Price + CCI | Cycle detection, OB/OS at +/-100 |
| `obv` | Price + On-Balance Volume | Volume confirms price? |
| `vwap` | Price + VWAP | Institutional fair value reference |
| `volume` | Price + Volume bars + RVOL | Volume spikes, confirmation |

### Decision tree

- "How's the price?" -> `line` or `candle`
- "Is it overbought?" -> `rsi` or `stochastic`
- "Trend strength?" -> `adx`
- "Momentum?" -> `macd`
- "Volatility?" -> `bollinger`
- "Volume confirming?" -> `volume` or `obv`
- "Full technical view" -> compose: `candle` + `macd` + `rsi` + `volume`

## Options

```
-p, --period    Time window: 30d, 60d, 90d, 1y, 2026, 2026-Q1  (default: 90d)
-w, --width     Chart width in columns                          (default: 80)
-H, --height    Chart height in rows                            (default: 24)
-g, --group     Disambiguate ticker across groups
--title         Override the auto-generated title
```

### Indicator-specific options

```
--ma sma:20 --ma ema:50     overlay: add moving averages (sma/ema/rma/dema/tema)
--fast 12 --slow 26         macd: EMA periods
--signal 9                  macd: signal line period
--rsi-period 14             rsi: lookback
--bb-period 20              bollinger: SMA period
--bb-width 2.0              bollinger: band width in std devs
--k 14 --d 3                stochastic: %K and %D periods
--adx-period 14             adx: lookback
--wr-period 14              williams-r: lookback
--cci-period 20             cci: lookback
--vol-period 20             volume: RVOL averaging period
```

## Examples

```bash
# Quick price check
lafmm chart line SPY --period 30d

# Candlestick with 90 days
lafmm chart candle NVDA --period 90d

# MACD momentum
lafmm chart macd NVDA

# Price with SMA(20) and EMA(50) overlaid
lafmm chart overlay NVDA --ma sma:20 --ma ema:50

# RSI overbought check
lafmm chart rsi AVGO --rsi-period 14

# Disambiguate when ticker exists in multiple groups
lafmm chart line SPY --group us-indices

# Full analysis (run multiple)
lafmm chart candle NVDA --period 60d
lafmm chart macd NVDA --period 60d
lafmm chart rsi NVDA --period 60d
lafmm chart volume NVDA --period 60d
```

## Data freshness

OHLCV data comes from CSV files updated by the daily-update skill.
Before rendering, consider whether the data is current enough for
what the user needs.

**Check freshness**: the chart title shows the date range
(e.g., "2026-01-21 to 2026-04-18"). If today is a trading day and
the latest date is not today, the data is stale.

**If the user wants current data**:
1. If the quote skill is configured, fetch the real-time price and
   mention it alongside the chart: "Chart shows through April 18.
   Current price from quote: $198.50 (+1.2%)."
2. If quote is not configured, suggest running daily-update first:
   "Data is through April 18. Run daily-update to update."
3. If the user doesn't need real-time, render as-is — the chart
   title makes the date range explicit.

**Weekend/holiday awareness**: if today is Saturday and the latest
date is Friday, the data is current — don't suggest fetching.

## Composition patterns

Charts are building blocks. Compose them to answer complex questions.

**Multi-indicator analysis**: run 3-4 chart commands in sequence,
then synthesize a narrative from all of them. Price action (candle)
for context, MACD for momentum, RSI for overbought/oversold,
volume for confirmation.

**Before/after zoom**: use `--period 90d` for the broad view, then
`--period 30d` to zoom into recent action. The contrast often
reveals whether a short-term move aligns with the longer trend.

**Cross-stock comparison**: run the same chart type for two stocks
(e.g., both leaders in a group) and compare. If NVDA's MACD crossed
up but AVGO's hasn't, that's divergence worth noting.

**Connect to Livermore signals**: after rendering, check cache/ for
the stock's current column state and recent signals. A chart showing
RSI > 70 means more when the engine just fired a SELL signal.

## Interpretation guidance

When presenting charts, connect observations to what they mean.
Don't just describe — interpret. But always frame as data, not advice.

- RSI > 70 with price at resistance: "RSI is elevated at 74,
  suggesting momentum may be stretched — though RSI can stay
  overbought for extended periods in strong trends."
- MACD crossover: "MACD line crossed above signal on April 15,
  which aligns with the engine's Natural Rally state."
- Volume spike on breakdown: "April 10 saw 3x average volume on
  the drop — institutional selling, not noise."
- ADX < 20: "ADX at 16 suggests no clear trend — range-bound
  conditions where trend-following signals are less reliable."

## Error handling

The subcommand prints clear messages to stderr and exits:
- **Ticker not found**: "NVDA not found in any group" — suggest checking
  the ticker name or running build-watchlist to add the sector.
- **Ambiguous ticker**: "NVDA found in multiple groups: semis, ai-power" —
  use `--group` to disambiguate.
- **Unknown chart type**: lists all 13 available types.
- **No data in period**: "no data in the requested period" — suggest
  widening the period or running daily-update.
- **Insufficient data for indicator**: indicators like SMA(50) need 50+
  data points. If the period is too short, the indicator line will be
  truncated or missing. Suggest a longer `--period`.

## Boundaries

- Charts are read-only views. They never modify data or engine state.
- Charts don't make trading recommendations. Present data clearly,
  let the user decide.
- If the user asks for an indicator not in the 13 types, say what's
  available and suggest the closest match.

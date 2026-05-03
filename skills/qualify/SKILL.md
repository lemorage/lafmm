---
name: qualify
description: >
  Qualify a stock for entry by evaluating three complementary
  perspectives: Momentum Breakout (SEPA), Range Trading, and Oversold
  Bounce. Works in two modes: Data mode (primary) — give a ticker and
  the skill computes all indicators from OHLCV data; Screenshot mode
  — paste any chart image and the skill extracts what it can visually.
  Use this skill when the user says "qualify NVDA", "does AAPL
  qualify", "is this buyable", "check this setup", "analyze this
  chart", shares a chart screenshot, or any variation that implies
  they want to know if a stock meets entry criteria.
---

# Qualify

Qualify a stock for entry from three independent perspectives, then
synthesize a single verdict. Each perspective covers a different market condition
— they complement, never conflict when applied correctly.

| Perspective | What it buys | Market condition | Hold period |
|-------------|-------------|-----------------|-------------|
| **Momentum Breakout** | Strength at pivotal points | Stage 2 uptrend | Weeks to months |
| **Range Trading** | Support within horizontal range | Sideways (Stage 1/3) | Days to 2 weeks |
| **Oversold Bounce** | Excessive decline recovery | Sharp pullback in bull market | 3-10 days |

## Mode detection

Determine the mode before anything else:

- **Data mode** — the user names a ticker (e.g., "analyze NVDA",
  "read AAPL"). Compute all indicators numerically from OHLCV CSVs.
  This is the primary mode: precise, no external tool needed.
- **Screenshot mode** — the user pastes a chart image. Extract values
  visually from the image. Platform-agnostic (TradingView, Webull,
  Thinkorswim, Yahoo Finance, or any charting tool).

If the user provides both a ticker and a screenshot, prefer data mode
for indicator values and use the screenshot for visual pattern
assessment (VCP shape, candle patterns, trendline slopes).

## Before analysis

### Gather system context

Read these files to personalize the analysis. Skip any that don't
exist. All paths are relative to `~/.lafmm/`.

1. **`profile.md`** — account size and risk tolerance for position
   sizing. If account size is specified, use it. If not, ask the user.
2. **`accounts/*/capital/*.csv`** — latest capital value (last row of
   most recent file). This is the actual number for position sizing.
3. **`cache/`** — if the ticker appears in any group, read its Livermore
   column state. Cross-reference: does the engine agree with your
   momentum assessment?
4. **`accounts/*/journal/`** — search for the ticker. If the user has
   traded it before, note their history: win rate, avg hold, last trade.
5. **`insights/`** — read the current year. If the agent has noted a
   pattern relevant to this setup (e.g., "tends to chase overextended
   entries"), flag it during analysis.
6. **`data/_meta/{TICKER}.json`** — if it exists, read sector, market
   cap, beta. Provides fundamental context without requiring the user
   to say anything.

### Check market context

Read `cache/market.md` for the broad market trend. This affects
confidence in every perspective:
- Market BULLISH → full confidence in momentum, higher bounce success
- Market NEUTRAL → reduced position sizes, prefer range setups
- Market BEARISH → oversold bounces are much riskier, momentum rarely
  works

If VIX/VIX3M data exists in `data/us-indices/_ref/`, check for regime:
RISK_OFF (VIX/VIX3M > 1.10 for 7+ days) means elevated caution across
all perspectives.

## Step 1: Load data and compute

This step loads all data and computes all technical indicators.
Perspective-specific values (support levels, panic lows) are
identified in Step 2 — those are analytical judgments, not indicator
computations. No subsequent step should re-read CSV files.

### Data mode

Find the ticker's OHLCV CSV in `data/{group}/{TICKER}/`. If the
ticker exists in multiple groups, use `--group` context or pick the
primary one. Concatenate year CSVs to build the full price series.

Render charts for visual pattern assessment (VCP shape, base
structure, trendline slopes):

```bash
lafmm chart candle <TICKER> --period 90d
lafmm chart overlay <TICKER> --ma sma:50 --ma sma:150 --ma sma:200 --ma ema:21
lafmm chart rsi <TICKER>
lafmm chart bollinger <TICKER>
lafmm chart volume <TICKER>
```

Compute all indicators numerically from the CSV:

| Indicator | Computation |
|-----------|-------------|
| Price (OHLC) | Last row of CSV |
| SMA 50, 150, 200 | Last value of `sma(close, N)` |
| EMA 21 | Last value of `ema(close, 21)` |
| Bollinger Bands | Last values of `bollinger(close, 20, 2.0)` → (mid, upper, lower) |
| RSI | Last value of `rsi(close, 14)` |
| ATR | Last value of `atr(high, low, close, 14)` |
| Volume today | Last row volume |
| Volume 50-day avg | Last value of `sma(volume, 50)` |
| 52-week high | `max(high[-252:])` |
| 52-week low | `min(low[-252:])` |
| Recent peak (3-month) | `max(high[-63:])` |
| SMA 200 (20 days ago) | `sma(close, 200)[-20]` — for trend slope |

Every number is exact — no estimation, no "UNREADABLE" fields.

**Staleness check**: read the date of the last CSV row. If it is more
than 1 trading day old (accounting for weekends and holidays), warn:
"Data through {date} — {N} trading days stale. Run daily-update
before analysis for current values."

#### Relative strength

Measures whether this stock is leading or lagging its peers and the
broad market. Computed as the ratio of cumulative returns:

```
RS = (stock_close / stock_close[N days ago])
   / (benchmark_close / benchmark_close[N days ago])
```

RS > 1.0 means the stock outperformed the benchmark over the period.
RS < 1.0 means it underperformed.

Compute two benchmarks, two lookbacks — four RS values total:

| Benchmark | Source | 50-day RS | 200-day RS |
|-----------|--------|-----------|------------|
| **SPY** (broad market) | `data/us-indices/SPY/` | — | — |
| **Sector median** | all tickers in `data/{group}/` | — | — |

For sector RS: compute the RS ratio for every ticker in the group
against SPY, then rank this ticker's RS within the group.

**Sector rank interpretation:**

| Percentile | Label |
|------------|-------|
| ≥ 75th | LEADER |
| 25th–75th | IN_LINE |
| ≤ 25th | LAGGARD |

**Cross-timeframe interpretation:**

| 50-day | 200-day | Reading |
|--------|---------|---------|
| LEADER | LEADER | Sustained strength — highest quality |
| LEADER | LAGGARD | Accelerating — recent turnaround, promising but unproven |
| LAGGARD | LEADER | Decelerating — was strong, losing momentum now |
| LAGGARD | LAGGARD | Sustained weakness — avoid for momentum setups |

#### Weekly trend confirmation

Checks whether the higher timeframe agrees with the daily picture.
Resample daily bars to weekly (group by ISO week, use last trading
day's close per week).

The weekly periods mirror the daily trend template for consistency:
SMA 10w approximates daily SMA 50, SMA 40w approximates daily SMA 200.

Three checks:

1. Price > SMA 10w (weekly short-term trend intact)
2. SMA 10w > SMA 40w (weekly MA alignment)
3. SMA 40w today > SMA 40w 4 weeks ago (weekly long-term trend rising)

| Score | Label |
|-------|-------|
| 3/3 | WEEKLY_CONFIRMED |
| 2/3 | WEEKLY_NEUTRAL |
| 0–1/3 | WEEKLY_DIVERGENT |

#### Earnings proximity

Read `data/_meta/_earnings.json`. If the ticker has a cached date:

| Condition | Label |
|-----------|-------|
| Earnings within 5 trading days (forward) | EARNINGS_IMMINENT |
| Earnings passed within 10 calendar days | POST_EARNINGS |
| Otherwise | EARNINGS_CLEAR |

If the ticker is not in the cache, run the earnings-calendar script
to fetch it. If it still returns nothing, label EARNINGS_UNKNOWN and
note that the date could not be determined.

POST_EARNINGS context: signals that form after an earnings report are
higher quality because the market has already repriced E[CF]. Note
this in the synthesis.

EARNINGS_IMMINENT context: the trend-based verdict may be overridden
by the earnings outcome in either direction. This is a risk factor,
not an automatic sizing reduction — the user decides whether to hold
through earnings. Flag it prominently.

### Screenshot mode

Extract indicator values visually from the chart image. Read from
legends, axis labels, and indicator panels — not from eyeballing line
positions.

Tips for different platforms:
- **TradingView** — values in the top-left legend next to indicator
  names (e.g., "SMA (50, close) 679.48")
- **Webull/Thinkorswim** — values often in a data panel or tooltip
- **Yahoo Finance** — limited indicators; may only have price + volume
- **Any platform** — axis scales give price range; volume bars have
  their own axis

Extract what you can. Mark any value that is not readable as
"UNREADABLE" and note which checks are affected. The minimum for
analysis is: price + SMA 50 + SMA 200.

**Screenshot mode limitations**: relative strength, weekly trend
confirmation, and earnings proximity cannot be computed from a
screenshot alone. State this explicitly in the output:

> "RS, weekly trend, and earnings proximity are unavailable in
> screenshot mode. These factors are not reflected in the confidence
> assessment below."

If the ticker is identifiable from the image AND exists in `data/`,
offer to switch to data mode: "I can see this is NVDA. Want me to
run data mode for exact values including RS and weekly trend?"

## Step 2: Run all three perspectives

Read the relevant reference files and evaluate:

1. **Momentum** — read `references/momentum.md`. Always run this first.
   The trend template score determines whether Range is applicable.
2. **Range** — read `references/range.md`. Only applicable if momentum
   trend template < 6/8 or SMA 50 is flat.
3. **Oversold** — read `references/oversold.md`. Only applicable if
   the stock has declined ≥ 20% from a recent peak.

Evaluate each perspective independently. Do not let one perspective's
conclusion influence another's evaluation. Then synthesize.

## Step 3: Assess the candlestick

**Data mode**: read the last 3–5 rows of the CSV. Compute body size
(`|close - open|`), upper shadow (`high - max(open, close)`), lower
shadow (`min(open, close) - low`), body as % of range
(`|close - open| / (high - low) × 100`). Identify patterns from the
numbers: hammer (lower shadow ≥ 2× body, small upper shadow), doji
(body < 5% of range), engulfing (today's body envelops yesterday's).

**Screenshot mode**: read the rightmost candle visually. Calculate
body size, shadows, body as % of range. Identify significant patterns
only when clearly visible.

If the candle is unremarkable, say so and move on.

## Step 4: Synthesize

### Perspective verdict

The decision tree for the final action:

1. If Momentum = BUY_NOW → final action follows momentum (strongest)
2. If Momentum = WATCH_FOR_BREAKOUT → set alert at pivot, prepare
3. If Momentum = WAIT_FOR_PULLBACK → check if Oversold applies
4. If Momentum = NO_SETUP or AVOID → check Range, then Oversold
5. If nothing applies → WAIT (no trade, hold cash)

### Confidence assessment

After determining the perspective verdict, assess conviction using
the cross-cutting factors from Step 1. These modify how much
confidence to place in the verdict — they do not change the verdict
itself.

| Factor | Effect |
|--------|--------|
| RS LEADER (sector) + RS > 1.0 vs SPY | Higher conviction |
| RS IN_LINE + RS ≈ 1.0 vs SPY | Neutral — no adjustment |
| RS LAGGARD (sector) + RS < 1.0 vs SPY | Lower conviction |
| WEEKLY_CONFIRMED | Higher conviction |
| WEEKLY_NEUTRAL | Neutral — no adjustment |
| WEEKLY_DIVERGENT | Lower conviction — daily and weekly disagree |
| POST_EARNINGS | Higher conviction if signal formed after the report |
| EARNINGS_IMMINENT | Risk flag — user decides, do not auto-adjust |

Synthesize the factors into one of three conviction levels:

- **High conviction** — RS leader, weekly confirmed, no earnings risk.
  Full position per perspective rules.
- **Normal conviction** — mixed or neutral factors. Standard sizing.
- **Low conviction** — RS laggard or weekly divergent. Reduce to 50%
  of calculated position, or skip if multiple negatives compound.

Present the reasoning explicitly: which factors support the verdict,
which argue against, and how they net out.

### Conflict safeguards

- Momentum ≥ 6/8 trend → Range is automatically NO_RANGE
- Momentum BUY_NOW and Oversold BUY cannot coexist (one buys highs,
  the other buys lows — if both seem to apply, re-evaluate)
- WEEKLY_DIVERGENT with Momentum BUY_NOW → downgrade to
  WATCH_FOR_BREAKOUT (weekly trend must confirm for immediate entry)
- When uncertain → default to the more conservative action

## Step 5: Position sizing

Read `references/position-sizing.md` for formulas. Use account size
from profile.md or latest capital CSV — never hardcode a default.

Apply the conviction level from Step 4:
- High conviction → full position per perspective rules
- Normal conviction → standard sizing (no adjustment)
- Low conviction → 50% of calculated shares

If EARNINGS_IMMINENT, note the gap risk alongside the position size.
Do not auto-halve — present the risk and let the user decide. Example:
"Calculated position: 150 shares ($X). Note: earnings in 3 days —
gap risk exists. Consider reducing if you do not intend to hold
through the report."

## Step 6: Cross-reference with LAFMM

If the ticker exists in `cache/`:
- Does the Livermore column agree with your momentum assessment?
- Are there active signals (BUY, SELL, DANGER)?
- Where are the pivotal points relative to current price?

If the user's genome data (from `lafmm stats --json`) shows this
setup type is a leak pattern for them, flag it clearly.

## Output format

Structure the response in this order:

1. **Data Extraction** — table of all indicator values. Data mode:
   exact numbers including RS, weekly trend, earnings status.
   Screenshot mode: extracted values + "UNREADABLE" notes +
   degradation notice for RS/weekly/earnings.
2. **Perspective A: Momentum** — trend template, stretch, VCP, volume,
   RSI, verdict
3. **Perspective B: Range** — identification, position, entry signals,
   verdict
4. **Perspective C: Oversold** — prerequisites, decline, signals,
   confirmation, verdict
5. **Synthesis & Final Action** — perspective verdict, confidence
   assessment (RS + weekly + earnings), conviction level, position
   sizing, action items, risks, what would change the verdict
6. **K-Line Note** — today's candle
7. **LAFMM Cross-Reference** — if data exists

Show all math explicitly. Write the formula, plug in numbers, show
the result. The user makes real money decisions from these numbers —
precision matters.

Present evidence, not predictions. The user decides what to do.

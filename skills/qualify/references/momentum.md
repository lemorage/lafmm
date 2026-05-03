# Momentum Breakout (Livermore-SEPA)

The primary system. Buys stocks breaking out of consolidation patterns
to new highs in confirmed uptrends. Based on Livermore's trend-following
principles and Minervini's SEPA methodology.

## Trend Template (8 conditions)

Evaluate each condition using extracted values. Show PASS/FAIL for each.

| # | Condition | How to evaluate |
|---|-----------|----------------|
| 1 | Price > SMA 150 | Direct comparison |
| 2 | Price > SMA 200 | Direct comparison |
| 3 | SMA 150 > SMA 200 | Direct comparison |
| 4 | SMA 200 trending upward | Data mode: `SMA_200_today > SMA_200_20d_ago`. Screenshot mode: is the line sloping up? If flat or declining → FAIL |
| 5 | SMA 50 > SMA 150 > SMA 200 | Direct comparison |
| 6 | Price > SMA 50 | Direct comparison |
| 7 | Price ≥ 52-week low × 1.25 | Data mode: exact from `min(low[-252:])`. Screenshot mode: estimate from visible range |
| 8 | Price within 25% of 52-week high | Data mode: exact from `max(high[-252:])`. Screenshot mode: estimate from visible range |

Score interpretation:
- **8/8**: Perfect trend. Proceed to all remaining checks.
- **6-7/8**: Good trend, minor weakness. Proceed with caution.
- **4-5/8**: Weak trend. Verdict → NO_SETUP. Skip remaining steps.
- **0-3/8**: Broken or downtrend. Verdict → AVOID.

## Stretch Check

How far price has extended beyond its mean. Overextended entries have
poor risk/reward because mean reversion pressure works against you.

**EMA 21 deviation:**

```
EMA21_Deviation = (Price - EMA21) / EMA21 × 100
```

| Deviation | Label | Position impact |
|-----------|-------|----------------|
| < 5% | SAFE | Full position |
| 5-10% | CAUTION | Max 50% of normal position |
| 10-15% | WARNING | Max 25% of normal position |
| > 15% | OVEREXTENDED | Do not enter — wait for pullback to EMA 21 |

**Bollinger Band position:**

```
BB_Position = (Price - BB_Lower) / (BB_Upper - BB_Lower) × 100
```

| Position | Zone |
|----------|------|
| 0-20% | Near lower band (pullback buy zone in uptrend) |
| 20-50% | Lower half (safe zone) |
| 50-80% | Upper half (getting warm) |
| 80-100% | Near upper band (overheated, don't chase) |
| > 100% | Above upper band (extreme) |

## VCP Pattern Assessment

Visually assess for a Volatility Contraction Pattern. A valid VCP
needs all elements visible on the chart:

1. **Prior uptrend** — clear upward movement before consolidation
2. **Consolidation base** — sideways in a tightening range, 2-8 weeks
3. **Contractions decreasing** — each pullback shallower (e.g., -15% → -8% → -4%)
4. **Volume declining** — bars progressively shorter during base, below 50-day average
5. **Pivot line** — clear horizontal resistance at the top (the breakout point)
6. **Bollinger squeeze** — bands narrowing confirms volatility contraction

Rate VCP status:
- **NONE**: No consolidation. Free-running trend or downtrend.
- **FORMING**: Base starting (1 contraction, or < 2 weeks old)
- **MATURE**: 2-3 contractions with decreasing depth, volume declining, pivot identifiable
- **BREAKING_OUT**: Price crossing above pivot with volume surge today
- **FAILED**: Base broke down below lower boundary on volume

If contractions are measurable, list each: from $X to $Y, depth -Z%.

## Volume Analysis

```
Volume_Ratio = Today_Volume / Avg_50_Volume
```

| Ratio | Label |
|-------|-------|
| < 0.5× | VERY_LOW |
| 0.5-0.8× | LOW |
| 0.8-1.3× | NORMAL |
| 1.3-2.0× | ABOVE_AVERAGE |
| 2.0-3.0× | HIGH |
| > 3.0× | EXTREME |

Context-dependent interpretation:
- Breaking out + HIGH/EXTREME volume = bullish confirmation
- Breaking out + LOW volume = suspect breakout (likely fake)
- In consolidation + declining volume = healthy base
- Pulling back in uptrend + LOW volume = healthy pullback
- Pulling back + HIGH volume = distribution (danger)
- New highs + EXTREME volume + long upper shadow = climax top

## RSI Assessment

| RSI | Label | Implication |
|-----|-------|-------------|
| < 30 | OVERSOLD | In uptrend, shouldn't happen. Possible trend break. |
| 30-40 | COOL | Pullback zone. Potential buy near support. |
| 40-55 | NEUTRAL | Healthy reset. Good for entries if other conditions met. |
| 55-65 | WARM_MOMENTUM | Has momentum, not overheated. Ideal entry zone. |
| 65-70 | GETTING_HOT | Approaching overbought. New entries carry pullback risk. |
| > 70 | OVERBOUGHT | Do not enter new momentum positions. |

Check for divergence:
- Price new highs + RSI lower highs = bearish divergence (weakening)
- Price new lows + RSI higher lows = bullish divergence (potential reversal)

## Verdicts

**BUY_NOW**: Trend ≥ 6/8 AND VCP = BREAKING_OUT AND Stretch ≤ CAUTION
AND RSI < 70 AND Volume_Ratio ≥ 1.5 (at least 50% above 50-day
average — the Minervini/O'Neil breakout volume standard) AND Position
feasible.

**WATCH_FOR_BREAKOUT**: Trend ≥ 6/8 AND VCP = MATURE AND Stretch <
WARNING AND RSI < 70. Specify the pivot price to watch.

**WAIT_FOR_PULLBACK**: Trend ≥ 6/8 but Stretch = WARNING or
OVEREXTENDED, OR RSI ≥ 65 with no VCP. Need price to return to EMA 21.

**ADD_TO_WATCHLIST**: Trend ≥ 6/8 but multiple secondary conditions
not met. Worth monitoring.

**NO_SETUP**: Trend < 6/8 or stock in unclear phase.

**AVOID**: Trend < 4/8, clear downtrend.

## Momentum Target (for R:R calculation)

Momentum trades are trend-following — there is no fixed price target
like range or oversold. Use these approximations for the R:R check:

- **VCP breakout**: measured move = base depth added to pivot price.
  If a VCP base corrected from $120 to $105 (depth = $15), the
  measured move target is pivot ($120) + $15 = $135.
- **General momentum**: if no VCP, use 2 × ATR above entry as a
  conservative short-term target for R:R feasibility.

R:R minimum for momentum: 2:1. If the measured move target does not
provide at least 2:1 against the stop (2 × ATR below entry), the
risk/reward is unfavorable even if all other conditions pass.

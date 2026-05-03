# Oversold Bounce

Short-term counter-trend recovery after excessive decline. Smaller
positions, faster exits than momentum. This is a tactical trade, not
a trend position.

## Prerequisites (all must pass)

1. SMA 200 is rising or at minimum flat. If declining → output
   "STRUCTURAL_BREAKDOWN: long-term trend is broken. This is a dying
   trend, not an oversold bounce. AVOID."

2. The stock had a prior uptrend (was strong before the decline).

3. The decline is short-term and sharp (not a slow grind over months).

4. **Cause assessment** — use the news-context skill to check whether
   the decline was caused by a broad market selloff (sector rotation,
   macro event, general panic) or by company-specific news (earnings
   miss, fraud, guidance cut, product failure). Company-specific
   declines are structurally different — the bounce may not come, or
   comes much weaker. If company-specific, require ALL 5/5 oversold
   signals instead of 3/5. In screenshot mode, if the ticker is not
   identifiable from the image, assume market-wide cause unless
   visible context (chart title, news overlay) suggests otherwise.

If prerequisites fail → NOT_OVERSOLD or STRUCTURAL_BREAKDOWN.

## Decline Assessment

```
Decline_Pct = (Close - Recent_Peak) / Recent_Peak × 100
```

Recent_Peak = highest price visible in the last 1-3 months.

| Decline | Classification |
|---------|---------------|
| 0% to -10% | NORMAL_PULLBACK — not a candidate |
| -10% to -20% | MODERATE — borderline, usually not deep enough |
| -20% to -30% | OVERSOLD — qualifies for analysis |
| -30% to -40% | DEEP_OVERSOLD — strong candidate if other conditions met |
| > -40% | EXTREME — very high risk, could be structural |

Must be at least -20% to proceed.

**Speed assessment:**
- ≤ 5 trading days = FAST (best bounce probability)
- 1-2 weeks = MODERATE_SPEED (acceptable)
- 3+ weeks = SLOW_GRIND (lower probability, may be structural)

## Oversold Signals (need ≥ 3 of 5)

1. RSI < 30 (ideally < 25 for strongest signal)
2. Price below Bollinger Band lower band
3. Price more than 15% below EMA 21 (negative stretch)
4. Price more than 10% below SMA 50
5. Climax selling volume: recent days showed volume ≥ 2× the 50-day
   average on red candles (panic exhaustion)

## Reversal Confirmation (need ≥ 2 of 5)

After oversold conditions are met, wait for confirmation:

1. Bullish reversal K-line near the low (hammer with lower shadow ≥ 2×
   body, bullish engulfing, or morning star)
2. RSI turning up: was below 30, now crossing back above 30
3. Volume declining after the panic spike (selling exhaustion)
4. Price recovering back inside Bollinger Band (was below, now inside)
5. Follow-through: green candle with close above prior candle's high

## Position Rules

These differ from momentum — the risk profile is different.

**Max position**: 15% of account (vs 25% for momentum)

**Stop loss**: Below the panic low by 2-3% or 1.5 × ATR below entry,
whichever is tighter

**Targets are modest and fast:**
- Target 1: EMA 21 → sell half (typically a 10-15% bounce)
- Target 2: SMA 50 → sell all remaining

**Time stop**: No meaningful bounce within 10 trading days → exit

**Do not convert to trend position.** If the bounce reaches SMA 50 and
you want to stay long, re-evaluate under the Momentum perspective from
scratch.

**Speed adjustment to position size:**
- FAST decline (≤ 5 days): highest probability → full 15% max
- MODERATE (1-2 weeks): good probability → 12% max
- SLOW_GRIND (3+ weeks): lower probability → 8% max or require 5/5
  oversold signals

**Market context adjustment:**
- Market BULLISH (from cache/market.md): full confidence
- Market NEUTRAL or unknown: reduce to 10% max
- Market recently broke SMA 50: 7% max or skip entirely

## Verdicts

**OVERSOLD_BUY**: Prerequisites pass AND decline ≥ -20% AND oversold
signals ≥ 3/5 AND reversal confirmations ≥ 2/5. Enter with reduced
position per the rules above.

**OVERSOLD_WATCH**: Prerequisites pass AND decline ≥ -20% AND oversold
signals ≥ 3/5 BUT confirmations < 2. Wait for confirmation.

**OVERSOLD_TOO_EARLY**: Prerequisites pass BUT decline < -20% OR
signals < 3/5. The selling may not be done yet.

**NOT_OVERSOLD**: Stock is not declining significantly, or is in a
normal pullback.

**STRUCTURAL_BREAKDOWN**: SMA 200 is declining. Not an oversold
condition — it's a structural trend change. AVOID.

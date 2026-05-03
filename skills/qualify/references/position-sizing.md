# Position Sizing

All position sizing uses the same risk framework: limit the maximum
loss per trade to a fixed percentage of capital. The formulas are the
same across perspectives — only the maximum position percentage and
stop distance calculation differ.

## Capital source

Read account size from these sources, in priority order:

1. **`accounts/*/capital/*.csv`** — last row of most recent file is
   the actual current NAV. This is the most accurate number.
2. **`profile.md`** — the user's stated account size. Use this if no
   capital CSV exists.
3. **Ask the user** — if neither exists, ask once and note the answer.

Never assume a default account size.

## Core formula

```
Max_Dollar_Risk = Account × Risk_Pct
```

Risk_Pct defaults to 2% (0.02). The user may override this in
`profile.md` under "Position Sizing" or "Hard Rules."

```
Stop_Distance = calculated per perspective (see below)
Max_Shares = Max_Dollar_Risk / Stop_Distance  (round DOWN)
Position_Value = Max_Shares × Price
Position_Pct = Position_Value / Account × 100
```

Show all arithmetic explicitly. Write the formula, plug in values,
show the result.

## Stop distance by perspective

**Momentum:**
```
Stop_Distance = 2 × ATR
Stop_Price = Close - Stop_Distance
```

**Range:**
```
Stop_Distance = Close - (Support × 0.98)   (support minus 2%)
  or: Stop_Distance = 1 × ATR             (whichever is tighter)
```

**Oversold:**
```
Stop_Distance = Close - (Panic_Low × 0.97)  (panic low minus 3%)
  or: Stop_Distance = 1.5 × ATR            (whichever is tighter)
```

**Guard**: if Stop_Distance ≤ 0 for any perspective, the trade is
invalid — price is already at or below the stop level. Do not enter.

## Position caps by perspective

| Perspective | Max position % of account |
|-------------|--------------------------|
| Momentum | 25% |
| Range | 20% |
| Oversold | 15% (adjusted by speed and market context — see oversold.md) |

Apply the cap: if Position_Pct exceeds the max, reduce shares.

## Stretch modifier (momentum only)

Apply the stretch label from the EMA 21 deviation check:

| Stretch | Modifier |
|---------|----------|
| SAFE | Full shares |
| CAUTION | 50% of calculated shares |
| WARNING | 25% of calculated shares |
| OVEREXTENDED | 0 shares (do not enter) |

## Conviction modifier

Apply the conviction level from the synthesis step's confidence
assessment (RS, weekly trend, earnings context):

| Conviction | Modifier |
|------------|----------|
| High | Full shares |
| Normal | Full shares |
| Low | 50% of calculated shares |

**Stacking rule**: when both stretch and conviction modifiers apply
(momentum only), use the more conservative of the two — do not
multiply them. Example: Stretch CAUTION (50%) + Low conviction (50%)
→ apply 50%, not 25%.

## Feasibility check

If Max_Shares < 1 after rounding down, the position is not feasible
at this account size. Report: "stock too expensive or volatile for
this account size" and note the minimum account needed:

```
Min_Account = Stop_Distance / Risk_Pct
```

This is not a criticism of the stock — it's a capital constraint.
Suggest alternatives with lower price or volatility if relevant.

## Concentration check

If `profile.md` specifies concentration limits (e.g., "max 30% in one
sector"), check the user's existing positions before recommending a
new one. If this trade would breach the limit, flag it.

## Risk:Reward

Calculate for every entry recommendation:

```
R:R = (Target - Entry) / (Entry - Stop)
```

Minimum acceptable: 1.5:1 for range, 2:1 for momentum, 1.5:1 for
oversold (using EMA 21 as target).

If R:R is below minimum, the setup is mathematically unfavorable even
if all other conditions are met. Note this clearly.

## Gap risk

This sizing assumes continuous price movement through the stop.
Overnight gaps, weekend gaps, and event-driven gaps (earnings, FDA
decisions, geopolitical events) can cause losses exceeding the
calculated 2% risk. For high-gap-risk situations — biotech, pre-
earnings, low-float stocks — consider reducing position size below the
formula output independently. The earnings-calendar skill flags
earnings proximity; for other binary events, use the news-context
skill to check for upcoming catalysts.

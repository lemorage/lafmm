---
name: position-size
description: >
  Use when the user asks "how much should I bet?", "position size",
  "how big should this trade be?", "what's my max drawdown?", "Kelly
  criterion", "risk sizing", or any variation about trade sizing or
  drawdown risk. Also use proactively when presenting a signal with
  high confidence from validate-signal, to pair the conviction with
  a concrete size recommendation.
---

# Position Size

Position sizing is where math becomes money. A great signal with the
wrong size produces either negligible returns (too small) or ruin
(too large). This skill provides the tools to size correctly.

## The script

`scripts/size.py` has two subcommands.

### Half-Kelly sizing

Given a signal's win rate and win/loss ratio, compute the optimal
fraction of capital to risk per trade.

```bash
uv run .claude/skills/position-size/scripts/size.py kelly 0.65 1.5
```

Arguments: win_rate (e.g. 0.65 = 65%), win_loss_ratio (avg win / avg
loss). These come from validate-signal's hit rate and from the user's
trade journal stats.

Half-Kelly gives roughly 75% of the growth rate of full Kelly with
dramatically less risk of ruin. Full Kelly assumes you know the true
parameters. You don't. Your estimates of win rate and ratio have error.
Half-Kelly absorbs that estimation error.

If the output is zero or negative, the signal has no edge. Do not trade
it, regardless of how the chart looks.

### Drawdown analysis

Historical max drawdown plus forward-looking Monte Carlo simulation
for a group's leaders.

```bash
uv run .claude/skills/position-size/scripts/size.py drawdown ~/.lafmm/data/semis
uv run .claude/skills/position-size/scripts/size.py drawdown ~/.lafmm/data/energy --json
```

**Options:**

- `--simulations N` — Monte Carlo paths. Default: 1000.
- `--horizon N` — trading days to simulate. Default: 252 (one year).
- `--json` — machine-readable output.

## Interpreting the output

**Half-Kelly fraction**: the maximum percentage of capital to risk on
a single trade. If Kelly says 10% and your account is $100K, you can
risk $10K on this trade. Your actual position size depends on where
your stop is: risk / (entry - stop) = shares. This is a ceiling, not
a target. Sizing below Kelly is always safer.

**Max drawdown**: worst peak-to-trough decline in the historical data,
with dates. This is what actually happened. The future will likely be
worse at some point.

**Monte Carlo percentiles**: simulated future drawdowns by resampling
historical returns. The 95th percentile is your planning number.
If the 95th percentile drawdown is 25%, you should expect a 25%
drawdown roughly once in 20 years. Can you survive that without
panicking? If not, reduce position sizes.

## Requirements

Kelly sizing needs a win rate and win/loss ratio from actual trade data.
Estimates from fewer than 20 round trips are unreliable -- the parameters
have wide confidence intervals. The drawdown subcommand needs at least
60 trading days of price history to produce meaningful Monte Carlo
results. More data means more realistic tail estimates.

## Connecting the pieces

The full sizing workflow:

1. **validate-signal** — get the hit rate and Sharpe for a signal
2. **stats** — get the win rate and avg win/loss from your journal
3. **position-size kelly** — compute the fraction from those numbers
4. **position-size drawdown** — check what drawdowns to expect
5. **Check profile.md** — does the result fit within the user's stated
   risk tolerance and concentration limits?

Present all of this together when recommending a size. The human makes
the final call.

## When to use this

- Before sizing any new position, especially after a period of strong
  signals where overconfidence is a risk.
- When validate-signal returns a high-conviction signal and the user
  needs a concrete size recommendation.
- After a drawdown, to reassess whether current position sizes are
  sustainable.
- When building a new group allocation and the user wants to understand
  worst-case drawdown scenarios.

## Limitations

Kelly assumes independent trades with known probabilities. Real
markets have serial correlation, regime shifts, and fat tails.
Half-Kelly provides a buffer but is not a guarantee. The Monte Carlo
simulation resamples from historical returns, so it cannot predict
unprecedented events (black swans, flash crashes). Treat the 95th
percentile as optimistic, not conservative.

---
name: factor-exposure
description: >
  Use when the user asks "is this alpha or just beta?", "what am I
  actually exposed to?", "factor analysis", "am I just riding the
  market?", or any variation about distinguishing skill from market
  exposure. Also use proactively when a group shows strong returns
  while the broad market is also up.
---

# Factor Exposure

A group in Upward Trend with strong returns may just be riding the
broad market. Factor regression separates genuine alpha (the return
you earned beyond what the market explains) from beta (your exposure
to market movements). If alpha is zero after controlling for beta,
the Livermore signals are not adding edge in that group.

## The script

`scripts/factor.py` regresses each leader's returns against SPY.

```bash
uv run .claude/skills/factor-exposure/scripts/factor.py ~/.lafmm/data/semis
uv run .claude/skills/factor-exposure/scripts/factor.py ~/.lafmm/data/energy --json
```

**Options:**

- `--benchmark PATH` — ticker directory for the benchmark. Defaults to
  `data/us-indices/SPY` (auto-discovered). Override for non-US markets
  or sector-relative analysis.
- `--json` — machine-readable output.

## Interpreting the output

**Alpha** (annualized): excess return not explained by market exposure.
Positive alpha means the group outperforms what its beta alone would
predict. Reported as a percentage per year.

**Alpha t-statistic**: statistical significance of the alpha estimate.
|t| > 1.96 is significant at 95% confidence (marked `**`).
|t| > 2.58 is significant at 99% confidence (marked `***`).
If not significant, you cannot distinguish the alpha from zero.

**Beta**: sensitivity to market moves. Beta 1.0 means the stock moves
1:1 with the market. Beta 1.5 means it moves 50% more than the market
in both directions. A "high return" from a beta-2.0 stock in a rising
market is not alpha. It's leveraged beta.

**R-squared**: fraction of the stock's return variance explained by
the market. R² of 0.80 means 80% of the stock's moves are market-driven.
Only the remaining 20% is stock-specific.

## Requirements

Both the group and the benchmark (SPY) need overlapping price history.
The regression needs at least 30 overlapping dates to produce
meaningful results. 60+ is preferable. The us-indices group provides
SPY data by default.

## When to use this

- When a group is performing well and you want to know if it's genuine
  edge or just market correlation.
- When comparing two groups with similar returns. The one with higher
  alpha and lower beta has the real edge.
- Before sizing a position based on validate-signal results. A signal
  with high Sharpe but pure beta exposure is not worth the same as one
  with genuine alpha.
- When the user's portfolio seems concentrated. If all groups have
  beta > 1.5, the portfolio is effectively leveraged to the market
  regardless of how many "sectors" it holds.

## Limitations

This is a single-factor model (market only). Adding sector ETFs as
additional factors would give a cleaner decomposition but requires
sector-specific benchmark data. The current implementation supports
additional factors via the library API (`factor_regression(strategy,
market, factors=[sector_returns])`) but the CLI wrapper uses market
only.

Alpha is backward-looking. A stock that showed alpha over the last
90 days may not show it over the next 90. Use rolling_alpha from the
library to check whether alpha is stable or decaying.

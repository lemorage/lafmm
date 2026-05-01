---
name: validate-signal
description: >
  Use when the user asks "is this signal real?", "should I trust this
  BUY signal?", "are my signals working?", "validate signals", "how
  reliable are the signals?", or any variation about signal quality or
  statistical significance. Also use proactively when presenting a new
  signal to the user, when signals seem to contradict the regime, or
  when the user has been whipsawed by recent signals.
---

# Validate Signal

The engine fires BUY, SELL, and DANGER signals based on Livermore's
rules. But a signal is only useful if it predicts something. This skill
tests whether a group's historical signals are statistically
distinguishable from random chance.

## The script

`scripts/validate.py` analyzes a group's leaders and reports signal
quality metrics.

```bash
uv run .claude/skills/validate-signal/scripts/validate.py ~/.lafmm/data/semis
uv run .claude/skills/validate-signal/scripts/validate.py ~/.lafmm/data/energy --signal SELL
uv run .claude/skills/validate-signal/scripts/validate.py ~/.lafmm/data/us-indices --horizon 10
```

**Options:**

- `--signal` — which signal type to test: BUY, SELL, DANGER_UP_OVER,
  DANGER_DOWN_OVER. Default: BUY.
- `--horizon N` — how many trading days after the signal to measure
  returns. Default: 5.
- `--permutations N` — number of random shuffles for the p-value test.
  Default: 10,000. More = more precise but slower.
- `--json` — machine-readable output.

## Interpreting the output

**Hit rate**: fraction of signals where the subsequent return moved in
the expected direction within the horizon. Above 55% is encouraging.
Below 50% means the signal is worse than a coin flip.

**Sharpe ratio**: mean return per signal divided by standard deviation
of returns. Measures reward relative to risk. Below 0.3 is noise.
Above 0.5 is tradeable. Above 1.0 is strong.

**p-value**: probability of seeing results this good by chance. The
permutation test shuffles signal dates 10,000 times and counts how
often random signals perform as well as the real ones. Below 0.05 is
statistically significant. Above 0.10 means you cannot distinguish
this signal from random.

**Signal decay**: mean return at 1, 5, 10, and 20 trading days after
the signal. Shows how long the signal's edge persists. If the 1d
return is positive but the 20d return is zero, the signal has a
short half-life. If returns grow with horizon, the signal captures
a real trend.

## What to do with the results

- **Significant signal (p < 0.05) with good Sharpe (> 0.5)**: the
  signal has statistical backing. Trust it more. Size positions with
  confidence.
- **Insignificant signal (p > 0.10)**: you cannot prove this signal
  beats random. Does not mean the signal is wrong, but you have no
  statistical evidence that it's right. Treat with caution.
- **Good hit rate but poor Sharpe**: wins are frequent but small,
  losses are rare but large. The signal catches direction but not
  magnitude.
- **Good Sharpe but poor hit rate**: wins are infrequent but large
  when they happen. The signal catches big moves but generates many
  small losers. Needs tight risk management.

## Requirements

Signals need history to validate. A group with 3 signals total cannot
produce meaningful statistics. The script requires at least 3 signals
of the requested type. More data means more reliable results. 20+
signals is ideal.

## When to use this

- Before acting on a signal, especially after a period of whipsaws.
  If the signal has no statistical backing, treat it with extra caution.
- When evaluating a new group's signal history before sizing positions.
- When signals from a group seem to contradict the regime detected by
  detect-regime.
- During periodic review to check whether the engine's edge is holding
  or decaying over time.

## Connecting to regime

A signal that tests well in a trending regime may test poorly in a
mean-reverting one. If detect-regime shows the sector is currently
mean-reverting, a historically significant BUY signal carries less
weight. Consider running validate-signal separately on trending and
non-trending periods to understand conditional signal quality.

## Limitations

Statistical significance is backward-looking. A signal that tested
well on 50 historical instances may stop working if the market regime
shifts. The p-value tells you about the past, not the future.

Small sample sizes produce unreliable results. 5 signals can appear
significant by chance. 20+ signals is the minimum for confidence.
The script enforces a floor of 3, but 3 is barely enough to compute
anything meaningful.

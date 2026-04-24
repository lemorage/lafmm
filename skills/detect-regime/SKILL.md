---
name: detect-regime
description: >
  Detect whether a sector is trending, mean-reverting, or random using
  the Hurst exponent and variance ratio test. Use this skill when the
  user asks "is this a good time for trend following?", "what regime is
  the market in?", "should I trust the signals right now?", "is this
  sector trending?", or any variation about market regime or whether
  the Livermore system is suitable for current conditions. Also use it
  proactively when signals seem noisy or contradictory, when
  tune-thresholds suggests extreme values, or before building a new
  watchlist group to assess whether the sector's price action favors
  trend-following.
---

# Detect Regime

The Livermore system is trend-following. It works when markets trend
(Hurst > 0.5). In mean-reverting environments, the engine produces
signals that are systematically late or wrong, buying at resistance
and selling at support. Knowing the regime tells you when to trust
the engine and when to step aside.

## The script

`scripts/regime.py` analyzes a group's leaders and reports the regime
for each.

```bash
uv run .claude/skills/detect-regime/scripts/regime.py ~/.lafmm/data/semis
uv run .claude/skills/detect-regime/scripts/regime.py ~/.lafmm/data/us-indices --json
```

**Options:**

- `--max-lag N` — Hurst exponent lag range. Default: 20. Larger values
  need more data but are more reliable.
- `--json` — machine-readable output.

## Interpreting the output

| Hurst | Regime | What it means for Livermore |
|-------|--------|---------------------------|
| > 0.55 | trending | Engine signals are reliable. Trends persist. |
| 0.45 to 0.55 | random | Coin-flip territory. Signals may or may not be meaningful. |
| < 0.45 | mean-reverting | Engine signals are likely wrong. Price reverts before trends confirm. |

The variance ratio test provides a second opinion. VR near 1.0 with a
high p-value means you cannot reject the random walk hypothesis. VR
significantly above 1.0 suggests trending. VR below 1.0 suggests
mean-reversion.

When leaders disagree on regime, exercise caution. A trending leader
paired with a mean-reverting leader produces a Key Price that reflects
neither environment cleanly.

## When to use this

- Before acting on a signal, especially after a period of whipsaws.
  If the regime is mean-reverting, the signal is more likely noise.
- When tuning thresholds. A mean-reverting regime needs wider
  thresholds (or the decision to stop tracking temporarily).
- When evaluating a new sector for the watchlist. A sector stuck in
  mean-reversion may not be worth tracking until the regime shifts.
- During the daily update, if the summary shows contradictory signals
  across a group's leaders.

## Limitations

Regime is not permanent. A sector can shift from trending to
mean-reverting in weeks. The Hurst exponent reflects the recent past
(determined by `--max-lag`), not a prediction of the future. Recheck
periodically, especially after major market events.

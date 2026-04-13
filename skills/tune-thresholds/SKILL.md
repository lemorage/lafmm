---
name: tune-thresholds
description: >
  Analyze a group's price volatility and suggest ATR-based swing/confirm
  thresholds for group.toml. Use this skill when setting up a new group and
  you need to pick initial thresholds, when signals seem noisy or too
  infrequent, when the user asks "are my thresholds right?", "why am I
  getting whipsawed?", "tune thresholds", or any variation that implies the
  current swing_pct or confirm_pct may not fit the stock's actual volatility.
  Also use it proactively before first analysis of a newly created group —
  default thresholds are guesses, ATR-derived ones are calibrated.
---

# Tune Thresholds

Livermore's column transitions depend on swing and confirm thresholds. If
these are wrong, everything downstream is wrong — the engine either
whipsaws on noise (thresholds too tight) or sleeps through real moves
(thresholds too loose). ATR (Average True Range) measures a stock's actual
daily volatility, giving us an objective basis for setting these values.

## The script

`scripts/atr.py` reads a group's OHLCV data, computes ATR for each leader,
and suggests swing_pct / confirm_pct values. It does not modify any files.

```bash
uv run scripts/atr.py ~/.lafmm/data/semis

uv run scripts/atr.py ~/.lafmm/data/us-indices --period 20

uv run scripts/atr.py ~/.lafmm/data/energy --multiplier 2.0
```

**Options:**

- `--period N` — ATR averaging window in trading days. Default: 14.
  Shorter periods (7-10) react faster to volatility changes. Longer
  periods (20-30) smooth out spikes. 14 is the standard starting point.
- `--multiplier X` — How many ATR% to use as the swing threshold.
  Default: 1.5. At 1.0× the swing equals normal noise — any average day
  could trigger a transition. At 2.0× only unusually large moves register.
  1.5× is a reasonable middle ground. Adjust based on how sensitive you
  want the system to be.

## How ATR works

True Range for a single day = the largest of:
- high − low (intraday range)
- |high − previous close| (gap up that retraced)
- |low − previous close| (gap down that retraced)

ATR = simple average of True Range over the last N days.

ATR% = ATR ÷ current price × 100. This normalizes across price levels —
a $5 ATR on a $100 stock (5%) means more than a $5 ATR on a $500 stock
(1%).

The script uses the **higher** of the two leaders' ATR% values. This
ensures the threshold isn't too tight for the more volatile leader, which
would cause false column transitions from its normal daily moves.

## How to use the output

The script prints current vs suggested values. Present this to the user
and ask before changing anything.

If the user agrees, update `group.toml`:

```toml
swing_pct = 8.7
confirm_pct = 4.4
```

Key Price thresholds are always 2× the stock thresholds — this is
hardcoded in the engine and does not need manual adjustment.

## When the defaults are wrong

- **Threshold barely exceeds ATR%**: the script warns about this. The
  engine is treating normal noise as signal. Expect frequent whipsaws
  between NR/NREAC columns with few confirmed UT/DT entries.
- **Threshold far exceeds ATR%** (>2.5× ratio): the engine is too
  sluggish. Real trend changes are absorbed as continuation within the
  current column. The stock could reverse 15% before the engine notices.
- **Leaders have very different volatility**: one leader is calm, the
  other is wild. The script uses the higher ATR% — but consider whether
  these two stocks actually belong in the same group. Livermore paired
  leaders that moved similarly.

## Choosing the period and multiplier

The defaults (period=14, multiplier=1.5) work for most US large-cap
equities. Adjust when:

- **Small-caps or high-beta stocks**: consider `--period 10` (faster
  response) or `--multiplier 1.2` (tighter threshold) — these stocks
  trend faster and need quicker detection
- **Stable sectors** (utilities, staples): consider `--period 20` and
  `--multiplier 1.5-2.0` — these stocks have lower volatility and you
  want to filter out more noise
- **During market stress** (VIX > 30): volatility spikes inflate ATR
  temporarily. Consider using a longer period or waiting for volatility
  to normalize before tuning

There is no universally correct answer — these are judgment calls. The
script gives you the data. You decide.

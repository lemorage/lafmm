---
name: stats
description: >
  Compute and display trading performance statistics. Use when the user
  asks about their performance, win rate, P&L, or wants a trading summary.
  Also use proactively at natural boundaries (end of quarter, end of year,
  after a significant drawdown or winning streak).
---

# Stats

Compute trading statistics from journal data and present them.

## Quick use

For the terminal display:

```bash
lafmm stats                      # all data
lafmm stats --period 2026        # year
lafmm stats --period 2026-Q1     # quarter
lafmm stats --period 2026-03     # month
lafmm stats --period 30d         # last 30 days
lafmm stats ibkr                 # specific account
lafmm stats --no-benchmark       # skip SPY comparison
```

For raw numbers (JSON):

```bash
python scripts/compute.py ACCOUNT_DIR [--period PERIOD] [--benchmark PRICE_DIR]
```

## What it computes

The compute script reads journal entries and daily capital CSV:

**Performance**: total trades, win rate, P&L, avg win/loss, expectancy
**Capital**: start/end capital, deposits, time-weighted return (TWR)
**Risk**: max drawdown, drawdown duration, win/loss streaks, Sharpe ratio
**Costs**: total fees, fees as % of P&L, dividends, tax, interest
**Behavior**: signal vs impulse trades (and win rate for each), order type distribution
**Exposure**: symbols traded, top symbols by P&L, monthly P&L
**Benchmark**: your return vs SPY over the same period

## Your role

The script computes the numbers. You interpret them in context of:

- **profile.md**: does performance match their stated goals and risk tolerance?
- **insights/**: do the numbers confirm or contradict patterns you've observed?
- **journal observations**: what was the human feeling during their best and worst trades?

The numbers are the mirror. Your interpretation connects them to the human's journey.

## Writing the summary

When asked for a full summary (or at natural boundaries), write to
`insights/{YEAR}-summary.md`. Structure:

1. **The Numbers**: cold facts from the compute output
2. **The Patterns**: what the data reveals about behavior
3. **The Evolution**: how the trader is changing, compared to their goals

Keep it honest. If they're losing money on impulse trades while their
signal-following trades are profitable, say so clearly.

## When to offer

- User asks: "How am I doing?" / "Show me my stats"
- End of month/quarter/year
- After a significant event: large drawdown, big win, strategy change
- When you notice a behavioral pattern that the stats would illuminate

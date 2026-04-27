---
name: stats
description: >
  Compute and display trading performance statistics. Use when the user
  asks about their performance, win rate, P&L, or wants a trading summary.
  Also use proactively at natural boundaries (end of quarter, end of year,
  after a significant drawdown or winning streak).
---

# Stats

Compute trading statistics from account data.

## Quick use

```bash
lafmm stats                          # visual
lafmm stats --json                   # JSON (for reasoning)
lafmm stats --period 2026            # year
lafmm stats --period 2026-Q1         # quarter
lafmm stats --period 30d             # last 30 days
lafmm stats ibkr                     # specific account
lafmm stats --json --period 2026-Q1  # combinable
```

Use `--json` when you need to reason about numbers.
Omit it when showing the user their stats.

## JSON output fields

```json
{
  "first_date": "2025-01-02",
  "last_date": "2025-06-30",
  "period": "all",
  "market_days": 125,
  "active_days": 80,
  "total_trades": 200,
  "buys": 95,
  "sells": 105,
  "round_trips": 45,
  "open_positions": 1,
  "wins": 30,
  "losses": 15,
  "breakeven": 0,
  "win_rate": 66.7,
  "total_pnl": 3500.00,
  "avg_win": 125.00,
  "avg_loss": -100.00,
  "largest_win": 800.00,
  "largest_loss": -600.00,
  "expectancy": 35.00,
  "profit_factor": 1.88,
  "concentration_pct": 35.0,
  "start_capital": 10000.00,
  "end_capital": 15000.00,
  "total_deposits": 1500.00,
  "total_withdrawals": 0.0,
  "total_fees": 80.00,
  "total_dividends": 30.00,
  "total_tax": 5.00,
  "total_interest": -10.00,
  "total_platform_fees": 0.0,
  "trading_return_pct": 30.0,
  "max_drawdown_pct": 12.0,
  "max_drawdown_days": 20,
  "longest_win_streak": 8,
  "longest_loss_streak": 4,
  "sharpe": 1.50,
  "fees_pct_of_pnl": 2.3,
  "pre_system_trades": 20,
  "pre_system_win_rate": 55.0,
  "post_system_trades": 80,
  "post_system_win_rate": 62.0,
  "signal_trades": 50,
  "signal_win_rate": 65.0,
  "discretionary_trades": 30,
  "discretionary_win_rate": 50.0,
  "order_types": {"limit": 150, "market": 30, "stop": 20},
  "avg_hold_days": 7.5,
  "longest_hold_days": 30,
  "longest_hold_symbol": "AAPL",
  "symbols_traded": 12,
  "top_symbols": [{"symbol": "AAPL", "pnl": 1200.00, "round_trips": 8, "wins": 6, "losses": 2, "win_rate": 75.0}, ...],
  "monthly_pnl": [{"month": "2025-01", "pnl": 500.00}, ...],
  "rolling": [{"window": 10, "trip_number": 10, "win_rate": 70.0, "expectancy": 50.00, "profit_factor": 1.80}, ...],
  "robustness": [
    {"excluded": "AAPL", "reason": "best", "round_trips": 40, "wins": 25, "losses": 15, "win_rate": 62.5, "expectancy": 20.00, "profit_factor": 1.30},
    {"excluded": "TSLA", "reason": "worst", "round_trips": 43, "wins": 30, "losses": 13, "win_rate": 69.8, "expectancy": 45.00, "profit_factor": 2.10}
  ],
  "genome": [
    {"code": "N-S-K-U", "trades": 9, "wins": 8, "losses": 1, "pnl": 1201.21, "win_rate": 88.9},
    {"code": "W-S-K-U", "trades": 6, "wins": 3, "losses": 3, "pnl": -827.30, "win_rate": 50.0}
  ],
  "spy_return_pct": 8.5
}
```

Key fields for analysis:
- `total_trades`: execution count (individual fills). `round_trips`: completed positions (flat→position→flat). `open_positions`: positions not yet flat
- `wins`, `losses`, `win_rate`, `expectancy`, `profit_factor`: all computed from round trips, not individual executions
- `rolling`: sliding window metrics over round trips (default window=10). shows edge stability over time
- `robustness`: leave-one-out analysis. excludes best/worst PnL symbols and recomputes metrics. `reason` is "best" or "worst"
- `trading_return_pct`: time-weighted return (TWR), matches IBKR
- `sharpe`: flow-adjusted (deposits/withdrawals subtracted before computing daily returns)
- `profit_factor`: gross wins / gross losses. >1.5 is good, >2 is excellent
- `concentration_pct`: % of absolute P&L from top symbol. >50% is risky
- `pre_system_trades` + `post_system_trades` = total round trips. pre-system = before `tracked_since`, post-system = after
- `signal_trades` + `discretionary_trades` = post-system. signaled = opened on a system signal, discretionary = opened without one
- `order_types`: dynamic dict. Keys are whatever order types appear in trades (limit, market, stop, stop_limit, trail, etc.)
- `avg_hold_days` / `longest_hold_days`: position hold duration from open→close reconstruction
- `genome`: trade genome classification. Each bucket has a 4-letter type code across 4 axes:
  - **Trend**: W (With-trend) / N (Neutral) / A (Against-trend). SMA 50/150/200 alignment at entry
  - **Cadence**: F (Flash <1d) / S (Swing 1-20d) / P (Position >20d). Actual hold duration
  - **Setup**: B (Breakout, within 1% of 50d high) / K (Pullback) / R (Reversal, within 5% of 50d low or RSI<30). Price structure at entry
  - **Volume**: C (Confirmed, rel_vol >1.4x) / U (Unconfirmed). Volume at entry vs 50d average
  - Example: `W-S-B-C` = With-trend Swing Breakout Confirmed. `?` = no OHLCV data for that ticker
  - Edge = top 3 by P&L (your strengths). Leak = bottom 3 by P&L (your weaknesses)
  - Populated automatically when `data/` exists in the workspace. Empty if no OHLCV data available
- `spy_return_pct`: benchmark, null if SPY data unavailable

## What it computes

**Performance**: executions, round trips, win rate, P&L, avg win/loss, expectancy, profit factor, order type distribution
**Capital**: start/end capital, deposits (exact USD via FXRateToBase), TWR
**Risk**: max drawdown, drawdown duration, win/loss streaks, Sharpe ratio (flow-adjusted)
**Costs**: trading fees, platform fees, dividends, tax, interest, fees as % of P&L
**Behavior**: pre-system vs post-system split, post-system further split into signaled vs discretionary, hold duration
**Genome**: 4-axis trade classification (Trend/Cadence/Setup/Volume) with edge/leak breakdown
**Exposure**: top symbols by P&L, concentration risk, monthly P&L breakdown
**Robustness**: leave-one-out analysis excluding best and worst performing symbols
**Rolling**: sliding window win rate, expectancy, profit factor over round trips
**Benchmark**: TWR vs SPY over the same period

## Your role

The script computes numbers. You interpret them in context of:

- **profile.md**: does performance match their goals and risk tolerance?
- **insights/**: do the numbers confirm or contradict patterns you've observed?
- **journal observations**: what was the human feeling during their best and worst trades?

## Writing the summary

When asked for a full summary (or at natural boundaries), write to
`insights/{YEAR}-summary.md`. Structure:

1. **The Numbers**: cold facts from the compute output
2. **The Patterns**: what the data reveals about behavior
3. **The Evolution**: how the trader is changing, compared to their goals

Keep it honest. If discretionary trades underperform systematic ones,
say so clearly.

### Using genome data

The genome reveals the trader's behavioral DNA. Use it to:
- **Edge/Leak**: edge types (top P&L codes) = natural strengths. Leak types (bottom P&L) = where they bleed. Flag when they're about to enter a leak-type trade.
- **Drift**: compare genome across periods (`--period 2026-Q1` vs `--period 2026-Q2`). If edge types disappear or leak types grow, the trader is drifting.
- **Mirror**: if the trader claims to follow a system, check if their genome matches. "You say trend-following, but 60% of your trades are A-S-R-U (against-trend reversal)."
- **Anchor insights to codes**: "Your N-S-K-U trades are 89% win rate, your strongest pattern. Your W-S-K-U trades are 50%, same setup in different trend context, loses edge."

## When to offer

- User asks: "How am I doing?" / "Show me my stats"
- End of month/quarter/year
- After a significant event: large drawdown, big win, strategy change
- When you notice a behavioral pattern that the stats would illuminate

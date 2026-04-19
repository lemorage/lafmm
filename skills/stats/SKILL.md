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
  "wins": 60,
  "losses": 40,
  "breakeven": 0,
  "win_rate": 60.0,
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
  "signal_trades": 50,
  "discretionary_trades": 30,
  "pre_system_trades": 20,
  "signal_win_rate": 65.0,
  "discretionary_win_rate": 50.0,
  "pre_system_win_rate": 55.0,
  "order_types": {"limit": 150, "market": 30, "stop": 20},
  "avg_hold_days": 7.5,
  "longest_hold_days": 30,
  "longest_hold_symbol": "AAPL",
  "symbols_traded": 12,
  "top_symbols": [{"symbol": "AAPL", "pnl": 1200.00}, ...],
  "monthly_pnl": [{"month": "2025-01", "pnl": 500.00}, ...],
  "spy_return_pct": 8.5
}
```

Key fields for analysis:
- `trading_return_pct`: time-weighted return (TWR), matches IBKR
- `profit_factor`: gross wins / gross losses. >1.5 is good, >2 is excellent
- `concentration_pct`: % of absolute P&L from top symbol. >50% is risky
- `signal_trades` / `discretionary_trades` / `pre_system_trades`: systematic vs discretionary vs pre-system
- `order_types`: dynamic dict — keys are whatever order types appear in trades (limit, market, stop, stop_limit, trail, etc.)
- `avg_hold_days` / `longest_hold_days`: position hold duration from open→close reconstruction
- `spy_return_pct`: benchmark, null if SPY data unavailable

## What it computes

**Performance**: total trades, win rate, P&L, avg win/loss, expectancy, profit factor, order type distribution
**Capital**: start/end capital, deposits (exact USD via FXRateToBase), TWR
**Risk**: max drawdown, drawdown duration, win/loss streaks, Sharpe ratio
**Costs**: trading fees, platform fees, dividends, tax, interest, fees as % of P&L
**Behavior**: systematic vs discretionary vs pre-system trades with win rates, hold duration
**Exposure**: top symbols by P&L, concentration risk, monthly P&L breakdown
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

## When to offer

- User asks: "How am I doing?" / "Show me my stats"
- End of month/quarter/year
- After a significant event: large drawdown, big win, strategy change
- When you notice a behavioral pattern that the stats would illuminate

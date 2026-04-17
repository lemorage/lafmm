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
  "active_days": 68,
  "total_trades": 150,
  "buys": 70,
  "sells": 80,
  "wins": 48,
  "losses": 30,
  "breakeven": 2,
  "win_rate": 60.0,
  "total_pnl": 3200.00,
  "avg_win": 135.50,
  "avg_loss": -105.00,
  "largest_win": 800.00,
  "largest_loss": -600.00,
  "expectancy": 40.00,
  "start_capital": 10000.00,
  "end_capital": 15200.00,
  "total_deposits": 2000.00,
  "total_withdrawals": 0.0,
  "trading_return_pct": 28.5,
  "max_drawdown_pct": 12.0,
  "sharpe": 1.55,
  "signal_trades": 25,
  "impulse_trades": 10,
  "pre_system_trades": 45,
  "signal_win_rate": 68.0,
  "impulse_win_rate": 50.0,
  "pre_system_win_rate": 57.8,
  "limit_orders": 120,
  "market_orders": 20,
  "stop_orders": 10,
  "symbols_traded": 12,
  "top_symbols": [{"symbol": "AAPL", "pnl": 1200.00}, ...],
  "monthly_pnl": [{"month": "2025-01", "pnl": 450.00}, ...],
  "spy_return_pct": 5.2
}
```

Key fields for analysis:
- `trading_return_pct`: time-weighted return (TWR), matches IBKR
- `signal_trades` / `impulse_trades` / `pre_system_trades`: systematic vs discretionary vs pre-system breakdown
- `pre_system_trades`: trades before `tracked_since` in account.toml, no Livermore signals
- `spy_return_pct`: benchmark, null if SPY data unavailable

## What it computes

**Performance**: total trades, win rate, P&L, avg win/loss, expectancy
**Capital**: start/end capital, deposits (exact USD via FXRateToBase), TWR
**Risk**: max drawdown, drawdown duration, win/loss streaks, Sharpe ratio
**Costs**: trading fees, platform fees, dividends, tax, interest
**Behavior**: systematic vs discretionary vs pre-system trades with win rates
**Exposure**: top symbols by P&L, monthly P&L breakdown
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

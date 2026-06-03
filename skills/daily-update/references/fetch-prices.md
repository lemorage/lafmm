# Fetch Prices

This step updates LAFMM's CSV price files with daily closing prices from
Yahoo Finance via yfinance. It handles the mechanical work of fetching,
deduplicating, and appending — so the data is always in the right format
for the engine.

## Data layout

Each ticker is a directory with one CSV per year:

```
data/us-indices/
├── group.toml
├── SPY/
│   ├── 2025.csv
│   └── 2026.csv
├── QQQ/
│   └── 2026.csv
```

This keeps files manageable over years. The loader reads all year files
for a ticker and concatenates them chronologically.

## The script

`scripts/fetch-prices.py` fetches closing prices and writes to
year-partitioned CSVs. It is idempotent — running it twice produces the
same result. Built-in throttling prevents rate limiting.

```bash
# Fetch all tracked tickers (skips those updated within 3 days)
./run .claude/skills/daily-update/scripts/fetch-prices.py

# Fetch specific tickers
./run .claude/skills/daily-update/scripts/fetch-prices.py NVDA AVGO

# Fetch one group
./run .claude/skills/daily-update/scripts/fetch-prices.py --group semis

# Force fetch all (even if recent)
./run .claude/skills/daily-update/scripts/fetch-prices.py --all
```

With no arguments, it discovers all tracked tickers by walking `data/`,
skips those already up to date, and fetches the rest with built-in
throttling. One invocation, no per-ticker orchestration needed.

## How to use it

### Daily update (most common)

```bash
./run .claude/skills/daily-update/scripts/fetch-prices.py
```

Discovers all groups and tickers, fetches only what is stale.

### Updating a specific group

```bash
./run .claude/skills/daily-update/scripts/fetch-prices.py --group us-indices
```

### Fetching specific tickers

```bash
./run .claude/skills/daily-update/scripts/fetch-prices.py NVDA AAPL SHOP
```

## What it produces

CSV files with OHLCV columns, one row per trading day:

```csv
date,open,high,low,close,volume
2026-01-02,128.50,131.20,127.80,130.00,45123000
2026-01-03,130.10,131.50,129.60,130.36,38901000
```

- **date**: YYYY-MM-DD, trading days only
- **open/high/low/close**: adjusted prices, 2 decimal places
- **volume**: daily trading volume

Adjusted prices account for stock splits and dividends, giving the
engine a continuous price series. The engine reads `close` for the
Livermore FSM. `open/high/low` are available for quant skills (ATR,
candlestick patterns). `volume` supports future liquidity analysis.

Stock splits are detected automatically via yfinance metadata. When a
split is found, historical CSVs are adjusted in place and a
`.splits_applied` marker records the event.

## Prerequisites

The script imports from the `lafmm` package. Run it with `./run` from
the workspace root. No manual setup needed.

## Error handling

- **Ticker not found**: prints a message to stderr, continues others.
- **Network failure**: exits without modifying CSVs. Run again later.
- **Rate limiting**: stops after 2 consecutive empty fetches.
- **Duplicate dates**: skipped automatically.
- **Cross-year data**: automatically partitioned into correct year files.

No partial writes — CSVs are either unchanged or have new complete rows.

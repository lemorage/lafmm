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

`scripts/fetch-prices.py` fetches closing prices for a ticker and writes to
year-partitioned CSVs. It is idempotent — running it twice produces the
same result.

```bash
# Append latest prices (auto-discovers ticker dir under ~/.lafmm/data/)
uv run .claude/skills/daily-update/scripts/fetch-prices.py NVDA

# Explicit target (directory or file)
uv run .claude/skills/daily-update/scripts/fetch-prices.py NVDA --csv ~/.lafmm/data/semis/NVDA

# Backfill from a specific date
uv run .claude/skills/daily-update/scripts/fetch-prices.py NVDA --start 2026-01-02

# Last 30 calendar days
uv run .claude/skills/daily-update/scripts/fetch-prices.py NVDA --days 30
```

The script prints each new row as it appends. If the data is already up
to date, it says so and exits.

## How to use it

### Updating one ticker

```bash
uv run .claude/skills/daily-update/scripts/fetch-prices.py SPY
```

Auto-discovers `~/.lafmm/data/us-indices/SPY/` and appends to the
current year's CSV.

### Updating an entire group

Read `group.toml` for tickers, then fetch each:

```bash
uv run .claude/skills/daily-update/scripts/fetch-prices.py SPY
uv run .claude/skills/daily-update/scripts/fetch-prices.py QQQ
uv run .claude/skills/daily-update/scripts/fetch-prices.py DIA
uv run .claude/skills/daily-update/scripts/fetch-prices.py IWM
```

### Populating a new group

Backfill with enough history for the engine to establish its state:

```bash
uv run .claude/skills/daily-update/scripts/fetch-prices.py NVDA --days 90
uv run .claude/skills/daily-update/scripts/fetch-prices.py AVGO --days 90
```

90 calendar days gives roughly 60 trading days.

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

## Prerequisites

The script uses PEP 723 inline metadata — `uv run` automatically installs
yfinance into a cached environment on first use. No manual setup needed.

## Error handling

- **Ticker not found**: prints a message, exits without modifying CSVs.
- **Network failure**: exits without modifying CSVs. Run again later.
- **Empty ticker dir**: creates it and writes data. Safe on new groups.
- **Duplicate dates**: skipped automatically.
- **Cross-year data**: automatically partitioned into correct year files.

No partial writes — CSVs are either unchanged or have new complete rows.

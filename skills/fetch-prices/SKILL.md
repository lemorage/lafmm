---
name: fetch-prices
description: >
  Fetch daily closing prices for stocks and ETFs, updating LAFMM CSV data
  files. Use this skill whenever the user wants to update price data, populate
  a new group's CSVs, backfill historical data, or when you notice data is
  stale during analysis. Also use it when the user says "fetch prices",
  "update prices", "get latest data", "pull prices for X", "backfill X",
  or any variation that implies they want fresh price data in their CSVs.
  Use it proactively before running sync or analysis when you see CSVs are
  missing or outdated.
---

# Fetch Prices

This skill updates LAFMM's CSV price files with daily closing prices from
Yahoo Finance via yfinance. It handles the mechanical work of fetching,
deduplicating, and appending — so the data is always in the right format
for the engine.

## The script

`scripts/fetch.py` does one thing: fetch closing prices for a ticker and
append new rows to its CSV. It is idempotent — running it twice on the same
day produces the same result.

```bash
# Append latest prices (auto-detects last date in CSV)
uv run scripts/fetch.py NVDA

# Explicit CSV path
uv run scripts/fetch.py NVDA --csv ~/.lafmm/data/semis/NVDA.csv

# Backfill from a specific date
uv run scripts/fetch.py NVDA --start 2026-01-02

# Last 30 calendar days
uv run scripts/fetch.py NVDA --days 30
```

The script prints each new row as it appends, so you can see exactly what
changed. If the CSV is already up to date, it says so and exits.

## How to use it

### Updating one ticker

```bash
uv run scripts/fetch.py NVDA --csv ~/.lafmm/data/semis/NVDA.csv
```

### Updating an entire group

Read `group.toml` to get the ticker list, then fetch each one:

```bash
# For each CSV in the group directory:
uv run scripts/fetch.py NVDA --csv ~/.lafmm/data/semis/NVDA.csv
uv run scripts/fetch.py AVGO --csv ~/.lafmm/data/semis/AVGO.csv
```

### Populating a new group

When a new group is created (either manually or via build-watchlist), the
CSVs are empty. Backfill with enough history for the engine to establish
its initial state — 60 trading days is a reasonable starting point:

```bash
uv run scripts/fetch.py NVDA --csv ~/.lafmm/data/semis/NVDA.csv --days 90
uv run scripts/fetch.py AVGO --csv ~/.lafmm/data/semis/AVGO.csv --days 90
```

90 calendar days gives roughly 60 trading days after weekends and holidays
are excluded.

### Updating all groups

Walk through `~/.lafmm/data/`, read each `group.toml` for tickers, and
fetch each one. Leaders and tracked stocks are all just CSVs — no special
handling needed.

## What it produces

CSV files with two columns, one row per trading day:

```csv
date,price
2026-01-02,130.00
2026-01-03,130.36
2026-01-06,129.10
```

- **date**: YYYY-MM-DD, trading days only (no weekends, no holidays)
- **price**: adjusted closing price, 2 decimal places

Adjusted close accounts for stock splits and dividends. This means the
engine sees a continuous price series without artificial jumps from
corporate actions.

## Prerequisites

The script uses PEP 723 inline metadata — `uv run` automatically installs
yfinance into a cached environment on first use. No manual setup needed.
The only requirement is that `uv` is available on PATH.

## Error handling

- **Ticker not found**: yfinance returns empty data. The script prints a
  message and exits without modifying the CSV.
- **Network failure**: yfinance raises an exception. The script exits
  without modifying the CSV. Run again when connectivity is restored.
- **CSV doesn't exist yet**: the script creates it with the header row
  and appends data. Safe to run on an empty group.
- **Duplicate dates**: skipped automatically. The script reads existing
  dates from the CSV and only appends new ones.

No partial writes — the CSV is either unchanged or has new complete rows.

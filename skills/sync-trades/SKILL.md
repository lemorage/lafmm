---
name: sync-trades
description: >
  Get trades into the journal. Two modes: user provides a broker CSV,
  or auto-fetch from IBKR API. Use when the user says "import my trades,"
  "sync my trades," provides a CSV, or wants to update their journal.
---

# Sync Trades

Get trade data from broker into the journal at
`accounts/{name}/journal/`. Two scripts handle the work:

- `scripts/fetch_ibkr.py` fetches CSV from IBKR's Flex Web Service API
- `scripts/parse_ibkr.py` parses CSV and writes journal markdown files

## Manual mode

User provides a CSV file:

```bash
uv run scripts/parse_ibkr.py /path/to/LAFMM.csv accounts/{name}/journal/
```

The script detects IBKR format, parses trades/cash/NAV, writes
journal files. Existing dates are skipped. Safe to re-run.

## Auto mode

Fetch from IBKR API, then parse:

```bash
uv run scripts/fetch_ibkr.py \
  --token "$(toml get accounts/{name}/account.toml broker.api.token)" \
  --query-id "$(toml get accounts/{name}/account.toml broker.api.query_id)" \
  --out /tmp/trades.csv

uv run scripts/parse_ibkr.py /tmp/trades.csv accounts/{name}/journal/
```

Read token and query_id from `accounts/{name}/account.toml`:

```toml
[broker.api]
type = "ibkr-flex"
token = "..."
query_id = "..."
```

The Flex Query uses a 90-day rolling window. Every fetch returns
recent data. Dedup skips existing entries. Run anytime.

## What the scripts produce

Each trading day gets a journal file: `journal/YYYY/MM-DD.md`

```markdown
# 2026/04-10

Capital: $13,036.74
Dividend: +USD 0.42 (GOOG)
Tax: -USD 0.06 (GOOG)
Interest: +USD 4.23

## Trades

| time | symbol | side | qty | price | fees | order | pnl | open_close | signal |
|------|--------|------|-----|-------|------|-------|-----|------------|--------|
| 09:45 | NVDA | buy | 50 | 148.30 | 0.35 | limit | — | O | — |
| 14:20 | AAPL | sell | 100 | 212.50 | 0.35 | stop | +320.00 | C | — |

## Observations
```

- **Capital**: total account value (cash + positions) from NAV in Base
- **Cash flows**: deposits, withdrawals, dividends, tax, interest, fees in original currency
- **signal**: starts as `—`, backfilled later from `cache/`

## After import

Report what changed. The parse script outputs JSON:

```json
{"trades": 3, "new_files": 1, "skipped": 46, "cash_flows": 0, ...}
```

Summarize for the user: "Synced 3 trades on 2026-04-10. 46 days
already up to date."

Then offer: "Want me to backfill signal alignment from cache?"

## Signal backfill

Cross-reference `cache/` signal history with journal trades.
For each trade date + symbol, check if a Livermore signal was
active. Fill the `signal` column. This is agent-driven — read
the cache markdown files, find matching signals by date and
ticker, then edit the journal files directly. No script needed.

Enables alignment analysis: how many trades followed a signal
vs. impulse.

## Setup

For IBKR Flex Query configuration, see `references/ibkr-setup.md`.

Future brokers: add a new parse script (e.g., `parse_schwab.py`).
Same journal output format, different input parsing.

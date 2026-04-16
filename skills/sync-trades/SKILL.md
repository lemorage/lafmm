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
- `scripts/parse_ibkr.py` parses CSV and writes journal + daily capital

## Manual mode

User provides a CSV file:

```bash
uv run scripts/parse_ibkr.py /path/to/LAFMM.csv accounts/{name}/
```

The script parses trades/cash/NAV and writes:
- `journal/` — trade entries for days with activity
- `capital/` — daily account value (every trading day from NAV)

Existing dates are skipped. Safe to re-run.

## Auto mode

Fetch from IBKR API, then parse:

```bash
uv run scripts/fetch_ibkr.py \
  --token "$(toml get accounts/{name}/account.toml broker.api.token)" \
  --query-id "$(toml get accounts/{name}/account.toml broker.api.query_id)" \
  --out /tmp/trades.csv

uv run scripts/parse_ibkr.py /tmp/trades.csv accounts/{name}/
```

Read token and query_id from `accounts/{name}/account.toml`:

```toml
[broker]
name = "Interactive Brokers"

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

**Timing**: the engine processes closing prices. A signal fires
AFTER market close on Day N. The trader sees it and acts on
Day N+1. For a trade on date D, check signals that existed
after processing D-1's close. The signal column records what
the trader could have been acting on, not what fired that day.

For each trade on date D:
1. Look up the stock in `cache/`
2. Check signals that fired on or before D-1
3. If a signal was active, fill it in

Only backfill entries after `tracked_since` from `account.toml`.
Entries before that date predate LAFMM — no signals existed.

Enables alignment analysis: how many trades followed a signal
vs. impulse.

## Setup

For IBKR Flex Query configuration, see `references/ibkr-setup.md`.

Future brokers: add a new parse script (e.g., `parse_schwab.py`).
Same journal output format, different input parsing.

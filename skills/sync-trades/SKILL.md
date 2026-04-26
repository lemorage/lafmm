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
uv run .claude/skills/sync-trades/scripts/parse_ibkr.py /path/to/LAFMM.csv accounts/{name}/
```

The script parses trades/cash/NAV and writes:
- `journal/` — trade entries for days with activity
- `capital/` — daily account value (every trading day from NAV)

Existing dates are skipped. Safe to re-run.

## Auto mode

Fetch from IBKR API, then parse:

```bash
uv run .claude/skills/sync-trades/scripts/fetch_ibkr.py \
  --token "$(toml get accounts/{name}/account.toml broker.api.token)" \
  --query-id "$(toml get accounts/{name}/account.toml broker.api.query_id)" \
  --out /tmp/trades.csv

uv run .claude/skills/sync-trades/scripts/parse_ibkr.py /tmp/trades.csv accounts/{name}/
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

**Rate limits**: IBKR enforces 1 request/sec, 10 requests/min per
token (error 1018). The fetch script handles this with backoff.
Activity data updates once daily after close. Fetch once per day.

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
| 09:45 | NVDA | buy | 50 | 148.30 | 0.35 | limit | — | O | BUY 10(d) |
| 14:20 | AAPL | sell | 100 | 212.50 | 0.35 | stop | +320.00 | C | SELL 10(b) |

## Observations
```

- **Capital**: total account value (cash + positions) from NAV in Base
- **Cash flows**: deposits, withdrawals, dividends, tax, interest, fees in original currency
- **signal**: filled automatically from `cache/` during import.
  For dates after `tracked_since`, the script looks up the most recent
  signal from D-1's close. `—` if no cache exists or date predates tracking.

## After import

Report what changed. The parse script outputs JSON:

```json
{"trades": 3, "new_files": 1, "skipped": 46, "cash_flows": 0, ...}
```

Summarize for the user: "Synced 3 trades on 2026-04-10. 46 days
already up to date."

If `cache/` does not exist yet, all signals will be `—`. Tell the
user: "Run daily-update first to enable signal tracking."

## Signal timing

The signal column records what signal the trader could have been
acting on. The engine processes closing prices. A signal fires
after market close on Day N. The trader sees it and acts on
Day N+1. The parse script handles this automatically: for a
trade on date D, it finds the most recent signal on or before D-1.

Only dates after `tracked_since` from `account.toml` get signals.
Earlier entries predate LAFMM — their signal stays `—`.

Post-`tracked_since` signal alignment enables the key question:
how many trades followed a Livermore signal vs. discretionary.

## Setup

For IBKR Flex Query configuration, see `references/ibkr-setup.md`.

Future brokers: add a new parse script (e.g., `parse_schwab.py`).
Same journal output format, different input parsing.

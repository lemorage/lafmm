---
name: quote
description: >
  Fetch real-time stock quotes. Use when the user asks "what's NVDA at?",
  "current price of X", or needs a live price for any US equity. Do not
  use for historical data (use fetch-prices) or news (use web search).
---

# Quote

Fetch real-time US equity prices from Finnhub.

## Quick use

```bash
uv run .claude/skills/quote/scripts/quote.py NVDA              # single ticker
uv run .claude/skills/quote/scripts/quote.py NVDA AAPL SPY     # multiple tickers
```

## JSON output

```json
{
  "symbol": "NVDA",
  "price": 148.30,
  "change": 2.50,
  "change_pct": 1.71,
  "open": 145.80,
  "high": 149.00,
  "low": 145.20,
  "prev_close": 145.80,
  "timestamp": "2025-06-15T19:30:00+00:00",
  "market_status": "open"
}
```

Fields:
- `price`: last traded price (real-time during market hours)
- `change` / `change_pct`: daily change from previous close
- `market_status`: `open` (<1 min since last trade), `recent` (<15 min), `closed` (>15 min)

For invalid tickers: `{"symbol": "XYZ", "error": "unknown ticker or no data"}`.

## When to use what

| Need | Tool |
|------|------|
| Current price of a stock | This skill |
| EOD price history for CSVs | fetch-prices |
| Company news, earnings, context | Web search |

## Rate limits

Finnhub free tier: 60 requests/min. Batch multiple tickers in one
call rather than running the script separately for each.

## Setup

Requires a Finnhub API key. Free at [finnhub.io](https://finnhub.io),
no credit card required.

Store in `~/.lafmm/config.toml`:

```toml
[finnhub]
api_key = "your-key-here"
```

The script also accepts `FINNHUB_API_KEY` env var as an override.
If neither is set, the script exits with setup instructions.
Help the user create `config.toml` if needed.

## Scope

US equities only (NYSE, NASDAQ). Finnhub returns zero for
unsupported symbols. The script reports these as errors.

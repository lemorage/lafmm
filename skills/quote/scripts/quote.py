#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///
"""Fetch real-time stock quotes from Finnhub.

Usage:
    uv run quote.py NVDA
    uv run quote.py NVDA AAPL SPY

Reads FINNHUB_API_KEY from environment.
Outputs JSON to stdout, diagnostics to stderr.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

API_URL = "https://finnhub.io/api/v1/quote"
_NETWORK_ERRORS = (requests.ConnectionError, requests.Timeout)


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    prev_close: float
    timestamp: int


@dataclass(frozen=True, slots=True)
class QuoteError:
    symbol: str
    reason: str


def fetch_quote(symbol: str, api_key: str) -> Quote | QuoteError:
    try:
        resp = requests.get(API_URL, params={"symbol": symbol, "token": api_key}, timeout=10)
    except _NETWORK_ERRORS:
        return QuoteError(symbol, "connection failed")

    if resp.status_code == 429:
        return QuoteError(symbol, "rate limited (60 req/min)")
    if resp.status_code != 200:
        return QuoteError(symbol, f"HTTP {resp.status_code}")

    data = resp.json()
    if data.get("c", 0) == 0:
        return QuoteError(symbol, "unknown ticker or no data")

    return Quote(
        symbol=symbol,
        price=data["c"],
        change=data["d"],
        change_pct=data["dp"],
        open=data["o"],
        high=data["h"],
        low=data["l"],
        prev_close=data["pc"],
        timestamp=data["t"],
    )


def format_quote(quote: Quote) -> dict:
    return {
        "symbol": quote.symbol,
        "price": quote.price,
        "change": quote.change,
        "change_pct": quote.change_pct,
        "open": quote.open,
        "high": quote.high,
        "low": quote.low,
        "prev_close": quote.prev_close,
        "timestamp": _iso_time(quote.timestamp),
        "market_status": _market_status(quote.timestamp),
    }


def format_error(error: QuoteError) -> dict:
    return {"symbol": error.symbol, "error": error.reason}


def _iso_time(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()


def _market_status(ts: int) -> str:
    age = datetime.datetime.now(tz=datetime.UTC).timestamp() - ts
    if age < 60:
        return "open"
    if age < 900:
        return "recent"
    return "closed"


def _log(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr)


def _resolve_api_key() -> str:
    key = os.environ.get("FINNHUB_API_KEY")
    if key:
        return key
    config = Path.home() / ".lafmm" / "config.toml"
    if config.exists():
        import tomllib

        with config.open("rb") as f:
            data = tomllib.load(f)
        key = data.get("finnhub", {}).get("api_key", "")
        if key:
            return key
    _log("Finnhub API key not found.")
    _log(f"Add to {config}:")
    _log("  [finnhub]")
    _log('  api_key = "your-key-here"')
    _log("Free key at https://finnhub.io")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch real-time stock quotes")
    parser.add_argument("symbols", nargs="+", help="One or more ticker symbols")
    args = parser.parse_args()

    api_key = _resolve_api_key()

    results = []
    for symbol in args.symbols:
        result = fetch_quote(symbol.upper(), api_key)
        match result:
            case Quote():
                results.append(format_quote(result))
            case QuoteError():
                _log(f"{result.symbol}: {result.reason}")
                results.append(format_error(result))

    output = results[0] if len(results) == 1 else results
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

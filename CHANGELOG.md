# Changelog

## 0.4.0

- new: braille canvas chart engine, universal renderer with 13 composers
- new subcommand: `lafmm chart` with chart skill for agent workspace
- new skill: daily-update for end-of-day orchestration
- new: quant layer with volatility (Parkinson, GK, RS, YZ) and correlation modules
- new: standard technical indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, etc.)
- TUI: help screen with signal and column legend
- charts: linear scaling for horizontal bars, value labels on vertical bars

## 0.3.0

- Rules 9(a-c) WATCH signals: pivot proximity alerts before buy/sell confirmation
- new skill: quote — real-time US equity prices via Finnhub
- new: `config.toml` for workspace-wide settings (API keys, preferences)
- stats: redesigned dashboard with charts, hold duration, profit factor, concentration risk
- stats: `--json` flag and `discretionary` terminology (was `impulse`)
- TUI: gold gradient for KEY signals, toggle KEY visibility with `k`
- TUI: signal list replaced with time-sorted DataTable
- IBKR fetch: handle XML error codes, add initial wait between API steps
- signal fill: automatic during trade import, uses D-1 close
- CLI: `-V`/`--version` and `-h`/`--help` flags
- agent prompt: "Real money, real time" section with quote skill and search guidance

## 0.2.0

- sync is now a subcommand: `lafmm sync` (or `$(cat .python) -m lafmm.sync_cache` from agent workspace)
- new skill: stats — trading performance analysis (`lafmm stats`)
- daily capital tracking via `accounts/{name}/capital/{YEAR}.csv`
- FX conversion for non-USD cash flows in journal entries
- signal backfill uses previous day's close (D-1) and excludes pre-system trades
- SessionStart hook injects `.version` into agent context on startup/resume
- `.version` now contains changelog notes for agent version awareness

## 0.1.0

- initial release

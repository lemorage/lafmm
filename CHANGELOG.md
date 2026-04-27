# Changelog

## 0.5.0

- new: trade genome classification (4-axis type codes: Trend/Setup/Cadence/Volume)
- new: genome panel in `lafmm stats` with proportion bars, edge/leak breakdown
- new: OHLCV auto-fetch and backfill for classification (`data/_adhoc/`)
- new indicators: RMA, ATR, true_range, stochastic, williams_r, CCI, DEMA, TEMA, ADX, OBV, VWAP, relative_volume
- fix: signal matching uses direction-aware walk-back instead of D-1 lookback
- refactor: ATR single source of truth in indicators.py (deduplicated from quant/volatility and classify)
- stats: per-symbol round-trip breakdown, rolling 10-trip metrics, robustness analysis
- stats: hierarchical behavior section with post-system split
- fix: round-trip based stats with flow-adjusted Sharpe
- new skill: detect-regime with Hurst exponent and variance ratio
- refactor: absorb fetch-prices and sync-cache scripts into daily-update skill
- fix: access yfinance columns by name instead of position (prevents silent data corruption)
- TUI: freeze first column in map table for horizontal scroll

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

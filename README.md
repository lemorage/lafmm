# LAFMM

**Livermore's Anticipating Future Movements Map** — Jesse Livermore's six-column price recording system from *How to Trade in Stocks* (1940), implemented as an interactive terminal tool and agent workspace.

## Install

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/lemorage/lafmm.git
cd lafmm && uv sync
uv tool install -e .
lafmm
```

Global install puts `lafmm` on PATH, including `~/.lafmm/` where agents operate. Without it, use `uv run lafmm` from the project directory.

First run scaffolds `~/.lafmm/`, fetches US index prices (SPY, QQQ, DIA, IWM), and launches [Claude Code](https://claude.ai/download) (v2.1.59+). Subsequent runs open the interactive TUI.

```bash
lafmm                          # TUI (default)
lafmm stats                    # trading performance
lafmm stats --period 2026-Q1   # filtered by period
lafmm sync                     # regenerate cache from data
lafmm chart macd NVDA          # terminal charts (13 types)
lafmm chart candle SPY -p 30d  # candlestick, last 30 days
lafmm tape today "bought NVDA" # record a trading thought
lafmm tape                     # list pending tapes
```

## The System

Two leaders per industry group. Each gets a 6-column sheet. Their combined price (Key Price) gets a third. 18 columns total.

```
| Leader A (6 cols) | Leader B (6 cols) | Key Price (6 cols) |
```

The engine records closing prices into six columns based on movement — only Upward Trend (green) and Downward Trend (red) use ink. The rest are pencil: tentative. Pivotal points mark where trends are decided. Signals fire when price confirms or fails at those points.

Group trend comes from Key Price, not individual stocks. Market trend = majority of groups agreeing.

> *"There is danger of being caught in a false movement by depending upon only one stock."*

## Workspace

```
~/.lafmm/
├── data/                       # OHLCV price data (TOML + CSV)
│   └── {group}/{TICKER}/{YEAR}.csv
├── cache/                      # computed Livermore state (markdown)
├── config.toml                 # workspace settings (API keys, preferences)
├── profile.md                  # who you are as a trader
├── accounts/                   # broker configs + trade journals
│   └── {name}/                 # one folder per trading account
│       ├── account.toml        # broker, type, instruments, fees
│       ├── capital/            # daily account value (NAV)
│       └── journal/            # trade logs + observations
├── insights/                   # agent's observations about you
├── memory/                     # Claude Code auto-memory
└── .claude/skills/             # auto-discovered by Claude Code
```

Add a sector: create a folder in `data/` with `group.toml` (leaders + thresholds) and ticker directories. The agent handles fetching, syncing, and analysis via skills.

## License

GPLv3.

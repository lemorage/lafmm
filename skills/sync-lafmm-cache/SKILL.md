---
name: sync-lafmm-cache
description: >
  Regenerate the cache/ directory from data/. Use this skill after
  fetching new prices, after adding or modifying a group, or whenever
  the cache is stale and you need fresh Livermore state for analysis.
  Also use it when the user says "sync", "update cache", "refresh
  analysis", "rebuild", or any variation that implies they want the
  engine to reprocess all price data and produce updated markdown.
  Use it proactively before any analysis that reads from cache/ — if
  prices have been fetched since the last sync, the cache is outdated.
---

# Sync LAFMM Cache

This skill regenerates `~/.lafmm/cache/` by running the Livermore
engine on all price data in `data/` and writing the results as
markdown. The cache is what you read when analyzing market state — it
must be in sync with the data for your analysis to be current.

## The command

```bash
$(cat ~/.lafmm/.python) -m lafmm.sync_cache
```

The `.python` file records the Python interpreter that has the lafmm
package installed. It is written during scaffold (`uv run lafmm`) and
points to the project's virtual environment Python.

**Options** (rarely needed):

```bash
$(cat ~/.lafmm/.python) -m lafmm.sync_cache --data /path/to/data --cache /path/to/cache
```

Override the default `~/.lafmm/data` and `~/.lafmm/cache` paths. Useful
for testing or custom setups.

## What it produces

```
cache/
├── market.md                # market trend + all groups summary table
└── {group}/
    ├── group.md             # 18-column Livermore Map + signals
    └── {TICKER}.md          # individual stock sheet, pivots, signals
```

Each file is self-contained — you can `cat` any single file and
understand the state without reading anything else.

**market.md** — the top-level view:
- Market trend (BULLISH / BEARISH / NEUTRAL)
- Summary table: each group's leaders, their column states, Key Price
  state, and group trend

**group.md** — the 18-column Livermore Map:
- Leaders' 6-column sheets side by side + Key Price's 6-column sheet
- All signals from both leaders and Key Price
- Tracked stocks listed with their current column

**{TICKER}.md** — individual stock detail:
- Current column, swing/confirm thresholds
- Entry count, pivotal point count, signal count
- Full 6-column sheet (all recorded entries)
- Active pivots with dates, prices, underline colors
- Active signals with rule citations

## When to sync

Sync is idempotent — running it twice produces the same output. The
cache is always a pure function of the data. There is no incremental
state to worry about.

**Always sync after:**
- Running fetch-prices (new price data needs processing)
- Adding or removing a group via build-watchlist
- Modifying group.toml (changing leaders, thresholds, start_col)

**The daily-update pattern:**
```
fetch-prices (all tickers) → sync → read cache → analyze
```

This is the standard daily workflow. Fetch fresh prices, regenerate
the cache, then read the updated markdown for analysis.

## What it does NOT do

- Does not fetch prices — run fetch-prices first
- Does not modify data/ — cache is derived from data, never the reverse
- Does not interpret signals — it records what the engine produces.
  Interpretation is your job during analysis

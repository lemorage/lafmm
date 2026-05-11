---
name: daily-update
description: >
  Run the end-of-day update workflow: sync trades, fetch prices,
  regenerate cache, and summarize what changed. Use this skill when the
  user says "daily update", "end of day", "update everything", "what
  happened today", "run the daily", "catch me up", or any variation
  that implies they want to bring all data current and see a summary.
  Also use it when the user opens a session after market close and
  hasn't updated yet today — check the most recent dates in cache/ and
  suggest running the daily if data is stale.
---

# Daily Update

The end-of-day ritual. This skill orchestrates the other skills in the
right order and produces a summary of what changed. No scripts. You
compose existing skills and read the results.

## The sequence

### 1. Sync trades (if accounts exist)

Check if `~/.lafmm/accounts/` has any account directories with
`account.toml`. If so, run the sync-trades skill for each account to
import today's executions.

Skip this step if no accounts are configured. The user may not have
connected a broker yet.

### 2. Fetch prices

Read every `group.toml` in `~/.lafmm/data/` to get the full ticker
list. Fetch closing prices for each ticker using the fetch script.
See `references/fetch-prices.md` for the command and options.

Run all tickers, leaders and tracked stocks across all groups.
The script is idempotent — fetching a ticker that's already current
is a no-op.

Parallelize: read each `group.toml` to get its tickers, then launch
one subagent per group, all in background. Each subagent runs the
fetch script for all tickers in its group. Do not loop sequentially
through 90+ tickers in a single bash command.

While prices fetch in background, start gathering data for step 4
that does not depend on cache: run `lafmm stats --json`, read
`tape.md`, read `insights/`, fetch quotes for open positions. When
all fetch subagents complete, verify prices, then run step 3.

**Verify prices** — after all fetches complete, run these checks
in parallel using subagents:

- **Staleness**: scan every ticker dir in `data/`. The latest
  CSV row's date must match the most recent trading day. Retry
  the fetch for any that are stale or missing.
- **Cross-reference**: pick tickers across different groups
  (at least one leader per macro sector). Run the quote skill
  for each. Compare the quote's close against the CSV's close
  for the same date. Any mismatch means the data may be
  corrupted — report to the user before proceeding.

Only proceed to step 3 after verification passes.

### 3. Sync cache

Regenerate all markdown in `cache/` from the updated price data.
See `references/sync-lafmm-cache.md` for the command.
This is where the engine processes today's close and produces any
new signals, column transitions, or pivotal points.

### 4. Summarize changes

Ground the summary in data before interpreting.

**Data pass.** Collect from these sources:

- `cache/market.md` for market trend and group summary
- Each `cache/{group}/group.md` for signals and column transitions
  (compare signal dates to the most recent trading day in the data)
- `lafmm stats --json` for current metrics, open positions, genome
- `accounts/*/capital/*.csv` latest row for actual account value
- Quote skill for current prices on any open position tickers
- Journal entries from step 1, with their signal column
  (auto-filled by the parse script)
- `tape.md` for the user's observations on today's trades
- `insights/{YEAR}.md` for last session's observations as
  comparison baseline
- For any significant move (5%+ daily, Key Price reversal, DANGER
  fired), run news-context skill to identify catalysts

**Present.** In this order, skip sections with nothing to report:

1. Signals. DANGER first (always prominent), then BUY/SELL with
   rule citations, resumption vs reversal distinguished
2. Transitions. Name them explicitly ("UT → NR", not "now in NR")
3. Market trend, if the bullish/bearish group count shifted
4. Trade alignment. Today's trades with their signal column from
   the journal. System-aligned or discretionary.
5. Open positions. Entry from journal, current from quote,
   unrealized computed in Python. System state from cache.
6. Performance delta. Key metrics from `lafmm stats --json` vs
   last session (return, win rate, Sharpe, post-system record).
   Note robustness (ex-best ticker expectancy).
7. News catalysts, only for significant moves flagged above

**Interpret.** After all data is presented, 2-4 sentences
connecting it. Anchor every claim to something from the data pass.
Cross-sector patterns, concentration observations, approaching
pivots.

### 5. Record observations (optional)

If you notice a behavioral pattern over multiple sessions (consistent
trading against signals, ignoring DANGER alerts, over-concentrating in
one sector), append a brief observation to
`~/.lafmm/insights/{YEAR}.md`.

This is for patterns that emerge over time, not one-off events. One
discretionary trade is normal. Ten consecutive discretionary trades
with no signal alignment is a pattern worth noting.

## Interaction principle

Steps 1-3 are mechanical — execute them and report progress briefly.
Do not pause between steps unless an error occurs.

Step 4 is the deliverable — present the summary clearly and pause.
The user may want to drill into specific groups, ask about specific
signals, or discuss what to do next.

Step 5 happens only when warranted — use your judgment.

## When data is stale

At the start of any session, check the most recent date in
`cache/market.md`. If it's earlier than the last trading day, suggest:
"Your data is from {date}. Want me to run the daily update?"

Weekends and holidays: the most recent trading day for US markets is
the last weekday that wasn't a market holiday. Don't suggest updates
on Saturday morning for Friday's data if it was already synced Friday
evening.

## What this skill does NOT do

- Does not make trading decisions. It presents what happened.
- Does not modify `group.toml`. Threshold tuning is a separate action.
- Does not add or remove groups. That's build-watchlist.
- Does not produce standalone performance analysis. That's the
  stats skill.

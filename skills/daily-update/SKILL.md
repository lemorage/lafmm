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
list. Fetch closing prices for each ticker using the fetch-prices
skill.

Run all tickers, leaders and tracked stocks across all groups.
fetch-prices is idempotent, so fetching a ticker that's already current
is a no-op.

### 3. Sync cache

Run the sync-lafmm-cache skill to regenerate all markdown in `cache/`
from the updated price data. This is where the engine processes today's
close and produces any new signals, column transitions, or pivotal
points.

### 4. Summarize changes

This is the core value of the daily update. Not the mechanical steps
above, but telling the user what matters.

Read `cache/market.md` and each `cache/{group}/group.md`. Compare with
what you know from the previous session (or from the signal history in
the cached files). Surface:

- **New signals** — any BUY, SELL, DANGER, or WATCH signals that fired
  today. Lead with these — they're the most actionable.
- **Column transitions** — any stock or Key Price that changed columns.
  A move from UT to NR is different from a move from NR to NREAC.
  Name the transition, not just the destination.
- **Market trend changes** — did the overall market trend shift? If
  multiple groups transitioned in the same direction, flag it.
- **Trade alignment** — if trades were imported in step 1, compare
  them to the signals. Did the user's trades follow Livermore signals
  or were they discretionary? This is a factual observation, not a
  judgment.

Keep the summary concise. The user can drill into any group by reading
the full cache files.

### 5. Flag surprises (optional)

If something unexpected happened (a stock dropped 5%+ in a day, a Key
Price reversed from confirmed trend, multiple DANGER signals fired
across groups), use the news-context skill to check for explanations.

Only do this when the data shows something that warrants investigation,
not on every daily update.

### 6. Record observations (optional)

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

Steps 5-6 happen only when warranted — use your judgment.

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
- Does not run stats. The user asks for performance analysis separately.

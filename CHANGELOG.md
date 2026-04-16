# Changelog

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

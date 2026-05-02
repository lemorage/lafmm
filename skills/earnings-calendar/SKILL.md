---
name: earnings-calendar
description: >
  Use when the user asks "any earnings coming up?", "who reports this
  week?", "earnings calendar", "what's reporting?", or any variation
  about scheduled earnings events. Also use proactively during
  daily-update to flag tickers reporting within the next 7 days, and
  when presenting a signal on a stock that reports soon.
---

# Earnings Calendar

Earnings reports are scheduled E[CF] events. Unlike news (which you
react to after it happens), earnings dates are known in advance.
Earnings are the single largest E[CF] catalyst type. A BUY signal
2 days before earnings carries different risk than one 2 weeks after.
This skill surfaces upcoming earnings so you can factor scheduled
catalysts into signal interpretation and position sizing decisions.

## The script

`scripts/earnings.py` scans all tracked tickers and reports upcoming
earnings dates. Results are cached at `data/_meta/_earnings.json`
with event-based staleness: a cached date is reused as long as it's
in the future. Once the earnings date passes, the next quarter's date
is fetched automatically. First run fetches all tickers; subsequent
runs only refetch tickers whose dates have passed.

```bash
uv run .claude/skills/earnings-calendar/scripts/earnings.py ~/.lafmm/data
uv run .claude/skills/earnings-calendar/scripts/earnings.py ~/.lafmm/data --group semis --days 7
uv run .claude/skills/earnings-calendar/scripts/earnings.py ~/.lafmm/data --cal
uv run .claude/skills/earnings-calendar/scripts/earnings.py ~/.lafmm/data --json
```

**Options:**

- `--group NAME` — scan only this group (directory name, e.g. `semis`).
- `--days N` — lookahead window in calendar days. Default: 14.
- `--cal` — display as a colored month grid instead of a list.
- `--json` — machine-readable output.

## Interpreting the output

The script lists tickers with earnings within the window, sorted by
date. For each ticker it shows the group, the date, and how many days
away it is.

What matters is not the earnings date itself but what it means for
your current positions and signals:

- **Signal + earnings in 1-3 days**: the signal is based on trend.
  Earnings can override the trend in either direction. The user
  decides whether to hold through or reduce exposure before the event.
- **Signal + earnings just passed**: post-earnings price action is
  often the most reliable. The market has repriced E[CF]. A BUY signal
  that forms after an earnings beat is stronger than one before.
- **No signal + earnings soon**: be alert. Earnings can trigger the
  column transition that produces a new signal. Watch for WATCH alerts
  (pivot proximity) around the earnings date.

## Requirements

The skill requires tracked tickers with price data in the data
directory. Internet access is required for the initial fetch and
for refreshing dates after earnings pass.

## When to use this

- When the user explicitly asks about upcoming earnings dates.
- Proactively during daily-update (step 4) to flag tickers reporting
  within 7 days.
- When presenting any signal, to check if earnings are imminent.
- Before sizing a new position, to understand catalyst timing.
- When a ticker shows unusual volume or price action without obvious
  news.

## Limitations

Yahoo Finance earnings dates are best-effort. Dates can shift, some
tickers return no data, and the timing field (pre-market vs
after-hours) is not always available. Treat this as a heads-up, not
an authoritative source. For exact timing, the user should verify
with their broker or the company's investor relations page.

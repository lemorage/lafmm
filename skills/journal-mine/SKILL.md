---
name: journal-mine
description: >
  Mine journal observations for behavioral patterns, hypothesis
  accuracy, and ticker-specific edge. Links free-text observations
  to trade outcomes via lafmm stats, accumulates intelligence in a
  scorecard that other skills consume. Use this skill when the user
  says "mine my journal", "update scorecard", "what have I learned",
  "reflect", "behavioral patterns", "observation accuracy", or any
  variation implying they want to extract intelligence from their
  trading observations.
---

# Journal Mine

Extract intelligence from journal observations. The journal is a
training set — each observation becomes a labeled sample once its
trade resolves. This skill links prose to outcomes and accumulates
evidence in a scorecard that informs future decisions.

The agent IS the NLP. No script can classify "I panicked and bailed"
as behavioral/panic. The agent reads, understands, links, and writes.
Python handles the arithmetic (via `lafmm stats --json`).

**Scorecard vs insights**: `insights/{YEAR}.md` captures qualitative
session-over-session observations (informal, append-only).
`scorecard.md` quantifies them — links observations to outcomes with
numbers, tracks resolution, computes hit rates. Insights notice;
scorecard proves.

## When to run

- Automatically as part of daily-update (after step 4, before the
  final summary). Run every time — incremental passes are cheap when
  no new observations exist.
- User explicitly asks ("mine my journal", "what have I learned")
- Weekly reflection sessions (full rescan for deeper analysis)

## Account scoping

This skill operates on one account at a time. If the user specifies
an account name, use it. If only one account exists in
`~/.lafmm/accounts/`, use it implicitly. If multiple exist and none
is specified, ask.

## Inputs

All paths relative to `~/.lafmm/`.

1. **`lafmm stats --json`** — quantitative backbone. Positions with
   P&L, per-symbol stats, genome codes, win rates. Never recompute
   what stats already provides.
2. **Journal observations** — `accounts/{name}/journal/{YEAR}/*.md`,
   the `## Observations` sections. Read only entries since the
   scorecard's last-updated date (incremental mode).
3. **Existing scorecard** — `accounts/{name}/scorecard.md`. The
   cumulative state from prior mining passes. If it doesn't exist,
   this is a first run — read all journals (full scan).
4. **Current prices** — use the quote skill to resolve pending
   time-bound predictions. Fall back to the latest CSV row only when
   the quote skill fails or markets are closed.
5. **`profile.md`** — reference for what has already graduated.
   Specifically check `## Edge Profile`, `## Leak Profile`, and
   `## Known Tendencies` sections. Don't duplicate patterns that
   are already there.

## Process

### Step 1: Anchor

Run `lafmm stats --json` for the account. This gives you:
- All closed positions with P&L, hold days, entry/exit prices
- Per-symbol breakdown (wins, losses, win rate)
- Genome classification per position (Trend/Setup/Cadence/Volume)
- Signal vs discretionary split

These numbers are truth. Use them directly. Never hand-count.

### Step 2: Scope

Read the scorecard's `Last updated` line. Identify which journal
entries are new since then. Read only those files.

If no scorecard exists or user requests full rescan: read all journal
files. This is expensive but self-healing.

### Step 3: Link

For each observation in scope:

1. Identify which ticker(s) it references (explicit mention or
   contextual — "sold everything" in a file dated 05-01 with an
   ACME sell in the trade table means the observation is about ACME)
2. Match to a position from stats output by date + ticker
3. Note the outcome: P&L, hold days, genome code, signal column

Some observations won't link to a specific trade (market-wide
thoughts, sector commentary). That's fine — classify them but mark
as unlinked.

### Step 4: Classify

For each linked observation, determine:

**Type** (what kind of observation is this):
- `hypothesis` — directional call or prediction ("will rally",
  "headed to 125", "uptrend will resume")
- `exit_reasoning` — why the user exited ("momentum too weak",
  "selling pressure overhead")
- `behavioral` — emotional state driving action ("panicked",
  "FOMO'd back in", "couldn't pull the trigger")
- `self_critique` — post-hoc assessment ("that was a mistake",
  "should have held")
- `market_read` — tape/context observation ("range-bound",
  "accumulation pattern", "sector rotation into semis")

**State** (emotional/conviction tone):
- `panic`, `FOMO`, `conviction`, `uncertain`, `frustrated`,
  `neutral`, `confident`, `greedy`

**Testable claim** (if applicable):
- Extract the prediction: ticker, direction, target, timeframe
- If no explicit timeframe, infer from context (swing = 2 weeks,
  position = 3 months) or mark as indefinite

### Step 5: Resolve pending

Read the scorecard's `## Pending` section. For each entry:

1. Check current price against the target/direction
2. If deadline has passed: resolve as accurate or inaccurate
3. If target hit before deadline: resolve as accurate
4. If neither: leave as pending

Move resolved predictions into the appropriate tally (Hypothesis
Accuracy section).

### Step 6: Update scorecard

Rewrite `accounts/{name}/scorecard.md` incorporating new evidence.
Each section updates incrementally — new observations add to existing
counts, they don't replace them.

Use numbers from `lafmm stats --json` directly for quantitative
claims. The agent's role is linking observations to those numbers
and spotting correlations, not recomputing statistics.

**Important**: Write concrete numbers, not vague assessments.
"8 observations, 87% accurate" not "mostly accurate". The stats
output gives you the P&L — use it.

### Step 7: Graduation check

Compare scorecard patterns against `profile.md`. If a pattern has:
- N >= 10 resolved observations
- Clear statistical significance (hit rate meaningfully above/below
  50%, or behavioral correlation with consistent direction)
- Not already in profile.md

Flag it in `## Ready to Graduate`. Do not auto-promote — present to
the user and let them confirm.

## Scorecard format

```markdown
# Scorecard

Last updated: YYYY-MM-DD | Evidence base: N resolved observations

## Ticker Edge

Per-symbol observation accuracy. Cross-reference with stats
per-symbol data. Only include tickers with 3+ observations.

Format: TICKER: N observations, X% accurate. [one-line insight]

## Behavioral Correlations

Emotional state → outcome patterns. Use stats P&L data for the
numbers.

Format: state → avg outcome $X vs hold (N=Y). [interpretation]

## Hypothesis Accuracy

Directional/thesis call hit rates, broken down by type when enough
data exists (mean-reversion calls, breakout calls, sector rotation
calls).

Format: category: X% hit rate (N=Y). [insight if notable]

## Pending

Unresolved time-bound predictions. One per line.

Format: YYYY-MM-DD | TICKER | "claim text" | check by YYYY-MM-DD

## Pattern Log

Newly discovered patterns (N >= 3). Date discovered, evidence
count, brief description. These are candidates for graduation.

## Ready to Graduate

Patterns with N >= 10 and statistical significance, awaiting user
confirmation for promotion to profile.md.
```

## Integration with other skills

### qualify

When qualify runs, it should read the scorecard for:
- Ticker-specific edge ("user reads SNXX exceptionally well")
- Behavioral warnings ("user tends to FOMO into this type of setup")
- Hypothesis track record ("user's mean-reversion calls are 78%
  accurate — weight their conviction higher")

### daily-update

Step 5 (record observations) can trigger journal-mine when it
notices the gap between scorecard's last-updated date and current
date spans 5+ closed positions.

### profile.md

Graduated patterns flow from scorecard → profile. The scorecard is
evidence; the profile is conviction. Both are read by the agent at
decision time, but profile carries more weight (it's confirmed).

## Full rescan mode

If the user says "rescan everything" or the scorecard is missing:
- Read ALL journal files regardless of date
- Rebuild scorecard from scratch
- This handles corruption, format changes, or fresh starts

## What this skill does NOT do

- Does not compute trade statistics (that's `lafmm stats`)
- Does not modify journal entries (journals are immutable truth)
- Does not auto-promote to profile.md (human confirms graduation)
- Does not make trading recommendations (that's qualify)
- Does not predict future outcomes from patterns

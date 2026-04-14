---
name: build-watchlist
description: >
  Research sectors, pick leader stocks, and scaffold or maintain groups
  in ~/.lafmm/data/. Use this skill when the user wants to start
  tracking a new sector, asks "what sectors should I watch?", "add
  semis to my watchlist", "which stocks should lead my energy group?",
  "set up a new group for X", or any variation that implies they want
  to evaluate and add a sector to their Livermore system. Also use it
  when you notice the user trades a sector they are not tracking, or
  when they ask for a broad market scan to find opportunities. Use it
  proactively when the user's journal shows repeated trades in an
  un-tracked sector. Also use it when you notice signs that an existing
  group may need revisiting — a leader's volume has dropped well below
  its sector peers, a tracked stock consistently outperforms both
  leaders, or a group has produced no meaningful signals for an extended
  period. These are signs the group configuration is stale.
---

# Build Watchlist

This skill covers both initial setup and ongoing maintenance of groups.
Markets rotate. Leaders change. A group set up six months ago may need
a leader swap, threshold re-tuning, or removal. The same workflow
applies whether you are building from scratch or revisiting.

## Interaction principle

Steps 1-3 (sector evaluation, leader selection, tracked stocks) involve
judgment — present your analysis with reasoning, then pause for human
confirmation before proceeding.

Steps 4-6 (check existing, scaffold, fetch/tune) are mechanical —
execute them and report results. Only pause if an error occurs.

Steps 7-8 (starting trend, final confirm) are a single checkpoint —
present everything together and ask once.

In short: research → pause → execute → report → confirm.

## The workflow

### 1. Identify the sector

The user may name a sector directly ("add semis") or ask you to scan
for opportunities. In either case, you need to determine whether the
sector is worth tracking right now.

Use the news-context skill to check for active catalysts. A sector
without catalysts can still be tracked — Livermore tracked sectors in
quiet periods too, because he wanted to see the column transition when
the trend started. But a sector with active catalysts is more
immediately useful.

Read `references/sector-criteria.md` for the evaluation framework and
the sector catalog with example leaders.

### 2. Pick two leaders

Leaders are the two most important stocks in the group. Their combined
price forms the Key Price, which determines the group's trend. Picking
the wrong leaders makes the entire group analysis unreliable.

`references/sector-criteria.md` has the full criteria. The short
version: pick the two highest-volume, most-representative stocks that
are correlated but not redundant (ideally different sub-sectors within
the sector).

If you are unsure which stocks best lead a sector, say so — the human
may have domain knowledge you lack. Present your candidates with
reasoning and let the human decide.

### 3. Optionally pick tracked stocks

Any additional stocks placed in the group directory are auto-discovered
as tracked stocks. They get their own engine but do not affect the Key
Price. These are useful for spotting divergence — if a tracked stock
enters Downward Trend while the Key Price is still in Upward Trend,
that tension is worth surfacing.

Tracked stocks are optional. Start with leaders only if the user is
unsure what else to include.

### 4. Check for existing group

Before scaffolding, check if the group already exists:

- If `data/{group}/group.toml` exists and the user wants to **add a
  tracked stock** — just create the ticker directory and fetch its
  prices. No group.toml change needed. The engine auto-discovers it.
- If the user wants to **change leaders** — warn them: changing leaders
  alters the Key Price retroactively. All existing Key Price pivots and
  signals will shift. The user must confirm before you proceed.
- If the group does not exist, continue to scaffolding.

### 5. Scaffold the group

Create the directory structure and group.toml. This is the concrete
output of the skill — files on disk that the engine can read.

```bash
# Create group directory
mkdir -p ~/.lafmm/data/{group}

# Create group.toml
cat > ~/.lafmm/data/{group}/group.toml << 'EOF'
name = "Semiconductors"
leaders = ["NVDA", "AVGO"]
swing_pct = 5.0
confirm_pct = 2.5
EOF

# Create ticker directories
mkdir -p ~/.lafmm/data/{group}/{TICKER}
```

Use `swing_pct = 5.0` and `confirm_pct = 2.5` as initial values. These
are placeholders — they get calibrated in the next step.

### 6. Fetch prices and tune thresholds

After scaffolding, invoke the other skills in order:

1. **fetch-prices** — backfill ~90 days of data for each ticker:
   ```bash
   uv run .claude/skills/fetch-prices/scripts/fetch.py NVDA --days 90
   uv run .claude/skills/fetch-prices/scripts/fetch.py AVGO --days 90
   ```

2. **tune-thresholds** — compute ATR-based thresholds from the fetched data:
   ```bash
   uv run .claude/skills/tune-thresholds/scripts/atr.py ~/.lafmm/data/{group}
   ```
   Present the suggested values to the user. If they agree, update
   `group.toml` with the new swing_pct and confirm_pct.

### 7. Determine starting trend

After fetching prices, check the last 30 days of each leader to decide
the initial column. If both leaders show higher highs and higher lows,
use `start_col = "UT"`. If both show lower highs and lower lows, use
`start_col = "DT"`. If ambiguous or leaders disagree, default to `"UT"`
and note to the user that the engine will self-correct after the first
full swing cycle — the first few pivots may not be meaningful.

Add `start_col` to `group.toml` if it differs from the default:

```toml
start_col = "DT"
```

### 8. Confirm with the user

Summarize what you set up: the group name, leaders, tracked stocks (if
any), the data range fetched, and the calibrated thresholds. Ask if
anything needs adjusting.

## Connecting to profile and journal

If `~/.lafmm/profile.md` specifies concentration limits (e.g., "max 5
sectors"), check how many groups already exist in `data/` before adding
a new one.

If `~/.lafmm/accounts/` has trade journals, scan for tickers the user
trades frequently that are not in any existing group. These are natural
candidates for a new watchlist group.

## Examples

**Example 1: Direct request**

User: "I want to track semiconductors"

You would: read sector-criteria.md, confirm NVDA + AVGO as leaders
(highest volume, different sub-sectors — GPU vs broadcom/networking),
ask if they want to track AMD or INTC too, scaffold the directory, fetch
90 days of prices, run tune-thresholds, present the result.

**Example 2: Opportunity scan**

User: "What sectors should I be watching right now?"

You would: use news-context to scan tier-1 feeds across multiple
sectors, identify which have active catalysts (earnings season in tech,
OPEC decision in energy, FDA rulings in biotech), present a ranked list
with reasoning, then scaffold whichever the user picks.

**Example 3: Proactive suggestion**

You notice the user's IBKR journal has 12 trades in biotech stocks over
the last month, but no biotech group exists in `data/`. You suggest:
"You've been active in biotech — want me to set up a group so the
Livermore system can track it?"

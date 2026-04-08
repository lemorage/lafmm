# LAFMM

**Livermore's Anticipating Future Movements Map** — an interactive terminal tool that implements Jesse Livermore's six-column price recording system from *How to Trade in Stocks* (1940).

You maintain CSV files with daily prices. The tool renders Livermore's map — column placement, pivotal points, trend confirmations, trading signals, Key Price, and market trend — all computed from the original rules.

## Quick Start

```bash
uv sync
uv run lafmm data/
```

## Setup

A **group folder** = one industry sector. It contains a `group.toml` and CSV files for its stocks.

```
data/
├── semis/
│   ├── group.toml      # config
│   ├── NVDA.csv         # leader
│   ├── AVGO.csv         # leader
│   └── AMD.csv          # tracked (optional, auto-discovered)
├── energy/
│   ├── group.toml
│   ├── XOM.csv
│   └── CVX.csv
```

**group.toml** — declares the two leader stocks and thresholds:

```toml
name = "Semiconductors"
leaders = ["NVDA", "AVGO"]
swing_pct = 8.0
confirm_pct = 4.0
```

**CSV files** — one row per trading day, append as you go:

```csv
date,price
2025-01-02,130.00
2025-01-03,133.00
```

The filename is the ticker (`NVDA.csv` → NVDA). If it matches a leader name in `group.toml`, it's a leader. Any other CSV is auto-discovered as a tracked stock.

## Usage

```bash
# full market dashboard — all groups at a glance
uv run lafmm data/

# single group — the 18-column Livermore Map
uv run lafmm data/semis/
```

No flags. No config beyond the folder. Point at a folder, get the map.

## Navigation

The app is an interactive TUI. Keyboard-driven:

| Key | Action |
|-----|--------|
| Arrow keys | Navigate rows |
| `Enter` | Drill into selected group or tracked stock |
| `Esc` | Go back one level |
| `Tab` | Switch focus between tables |
| `q` | Quit |

Three levels of navigation:

1. **Dashboard** — all groups listed with leader states, Key Price, and market trend
2. **Group** — the 18-column Livermore Map + signals + tracked stocks list
3. **Stock** — an individual tracked stock's 6-column sheet + pivots + signals

## The System

### The Six Columns

Every price is recorded into exactly one of six columns each day:

```
| SecRally | NatRally | UPTREND | DNTREND | NatReac | SecReac |
|  pencil  |  pencil  |  BLACK  |   RED   | pencil  | pencil  |
```

- **Upward Trend** (black ink → green in terminal) — confirmed uptrend
- **Downward Trend** (red ink → red in terminal) — confirmed downtrend
- **Natural Rally / Natural Reaction** (pencil → gray) — normal counter-moves
- **Secondary Rally / Secondary Reaction** (pencil → gray) — weak, indecisive moves

Only the two trend columns use ink. The rest are pencil — tentative, unconfirmed.

### Swing and Confirm

Two thresholds control column transitions:

- **Swing** — how far price must move to leave a column (~6 points for stocks, ~12 for Key Price)
- **Confirm** — how far past a pivotal point to confirm a trend change (half the swing)

Set `swing_pct` in `group.toml` for percentage-based thresholds. The tool converts to absolute points from each stock's starting price.

### Pivotal Points

When price leaves a column, the last price in that column becomes a **pivotal point** — underlined in the map:

- **Red underline** — leaving Upward Trend or Natural Reaction (marks a high to watch)
- **Black underline** — leaving Downward Trend or Natural Rally (marks a low to watch)

> *"It is after two Pivotal Points have been reached that these records become of great value to you in helping you anticipate correctly the next movement of importance."*

### Trading Signals

Four signals based on price behavior at pivotal points:

| Signal | Meaning |
|--------|---------|
| **BUY** | Uptrend resumed, or downtrend confirmed over |
| **SELL** | Downtrend resumed, or uptrend confirmed over |
| **DANGER: Up Over** | Rally failed near prior high — uptrend may be finished |
| **DANGER: Dn Over** | Reaction held near prior low — downtrend may be finished |

Signals are advisory. The system shows what price action means — you decide whether to act.

### The 18-Column Map

Livermore never analyzed a single stock alone. He tracked **groups** — two leader stocks from the same industry:

```
| Leader A (6 cols) | Leader B (6 cols) | Key Price (6 cols) |
```

- **Leaders** — each runs its own 6-column engine
- **Key Price** — the combined price (A + B) runs through a third engine with doubled thresholds (swing=12, confirm=6)

The group trend comes from the Key Price column, not from individual stocks.

> *"There is danger of being caught in a false movement by depending upon only one stock. The movement of the two stocks combined gives reasonable assurance."*

### Tracked Stocks

Any CSV in a group folder that isn't a leader is a **tracked stock**. It gets its own engine but doesn't affect the Key Price or group trend. It's there for your reference — drill in from the group view to see its sheet.

### Market Trend

With multiple groups, the market trend is the majority:

- \>60% of groups bullish → **market bullish**
- \>60% of groups bearish → **market bearish**
- Otherwise → **neutral**

## group.toml Reference

```toml
name = "Semiconductors"       # display name
leaders = ["NVDA", "AVGO"]    # exactly 2, match CSV filenames
swing_pct = 8.0               # swing as % of starting price (default: 6.0)
confirm_pct = 4.0             # confirm as % (default: 3.0)
start_col = "UT"              # initial trend: "UT" or "DT" (default: "UT")
```

## License

GPLv3.

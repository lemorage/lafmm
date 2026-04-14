# LAFMM Rules — Livermore Market Key Specification & Design

***

## Part I: Original Rules — Verbatim Transcription & Formal Specification

Every line of code in this project **must trace back to a numbered rule**. This section establishes the **single source of truth**.

***

### Rule 1 — Ink: Upward Trend

> _"Record prices in Upward Trend column in black ink."_

**Formal Spec:**

| Field   | Value                                             |
| ------- | ------------------------------------------------- |
| Trigger | Any price recorded into column `UT`               |
| Action  | Mark entry with `ink = "black"`                   |
| Visual  | TUI: `bold white` / `bold green` on dark terminal |

***

### Rule 2 — Ink: Downward Trend

> _"Record prices in Downward Trend column in red ink."_

**Formal Spec:**

| Field   | Value                               |
| ------- | ----------------------------------- |
| Trigger | Any price recorded into column `DT` |
| Action  | Mark entry with `ink = "red"`       |
| Visual  | TUI: `bold red`                     |

***

### Rule 3 — Ink: Other Four Columns

> _"Record prices in the other four columns in pencil."_

**Formal Spec:**

| Field   | Value                                                   |
| ------- | ------------------------------------------------------- |
| Trigger | Any price recorded into `SR`, `NR`, `NREAC`, or `SREAC` |
| Action  | Mark entry with `ink = "pencil"`                        |
| Visual  | TUI: `dim` (gray)                                       |

***

### Rule 4(a) — Pivot: Leaving Upward Trend

> _"Draw red lines under your last recorded price in the Upward Trend column the first day you start to record figures in the Natural Reaction column. You begin to do this on the first reaction of approximately six points from the last price recorded in the Upward Trend column."_

**Formal Spec:**

| Field     | Value                                                                               |
| --------- | ----------------------------------------------------------------------------------- |
| Trigger   | Transition from `UT` → `NREAC` (via Rule 6a)                                        |
| Condition | `last_UT - price >= swing`                                                          |
| Action    | Create `PivotalPoint(source_col=UT, underline="red")` at `last[UT]`                 |
| Meaning   | **Marks the high-water mark of the upward trend — the price to beat on next rally** |

***

### Rule 4(b) — Pivot: Leaving Natural Reaction

> _"Draw red lines under your last recorded price in the Natural Reaction column the first day you start to record figures in the Natural Rally column or in the Upward Trend column. You begin to do this on the first rally of approximately six points from the last price recorded in the Natural Reaction column."_
>
> _"You now have two Pivotal Points to watch, and depending on how prices are recorded when the market returns to around one of those points, you will then be able to form an opinion as to whether the positive trend is going to be resumed in earnest — or whether the movement has ended."_

**Formal Spec:**

| Field     | Value                                                                     |
| --------- | ------------------------------------------------------------------------- |
| Trigger   | Transition from `NREAC` → `NR` or `UT` (via Rule 6d)                      |
| Condition | `price - last_NREAC >= swing`                                             |
| Action    | Create `PivotalPoint(source_col=NREAC, underline="red")` at `last[NREAC]` |
| Meaning   | **Marks the low-water mark of the reaction — support level to watch**     |

***

### Rule 4(c) — Pivot: Leaving Downward Trend

> _"Draw black lines under your last recorded price in the Downward Trend column the first day you start to record figures in the Natural Rally column. You begin to do this on the first rally of approximately six points from the last price recorded in the Downward Trend column."_

**Formal Spec:**

| Field     | Value                                                                                    |
| --------- | ---------------------------------------------------------------------------------------- |
| Trigger   | Transition from `DT` → `NR` (via Rule 6c)                                                |
| Condition | `price - last_DT >= swing`                                                               |
| Action    | Create `PivotalPoint(source_col=DT, underline="black")` at `last[DT]`                    |
| Meaning   | **Marks the low-water mark of the downward trend — the price to break on next reaction** |

***

### Rule 4(d) — Pivot: Leaving Natural Rally

> _"Draw black lines under your last recorded price in the Natural Rally column the first day you start to record figures in the Natural Reaction column or in the Downward Trend column. You begin to do this on the first reaction of approximately six points from the last price recorded in the Natural Rally column."_

**Formal Spec:**

| Field     | Value                                                                  |
| --------- | ---------------------------------------------------------------------- |
| Trigger   | Transition from `NR` → `NREAC` or `DT` (via Rule 6b)                   |
| Condition | `last_NR - price >= swing`                                             |
| Action    | Create `PivotalPoint(source_col=NR, underline="black")` at `last[NR]`  |
| Meaning   | **Marks the high-water mark of the rally — resistance level to watch** |

***

### Rule 5(a) — Confirmation: Natural Rally → Upward Trend

> _"When recording in the Natural Rally column and a price is reached that is three or more points above the last price recorded in the Natural Rally column (with black lines underneath), then that price should be entered in black ink in the Upward Trend column."_

**Formal Spec:**

| Field           | Value                                               |
| --------------- | --------------------------------------------------- |
| Precondition    | Currently recording in `NR`                                       |
| Pivot reference | Last pivotal point in `NR` with `underline="black"`               |
| Condition       | `price >= pivot_NR_black.price + confirm`                         |
| Action          | Record price in `UT` (black ink)                                  |
| Meaning         | **Upward trend confirmed — reversing from downtrend or resuming** |

***

### Rule 5(b) — Confirmation: Natural Reaction → Downward Trend

> _"When recording in the Natural Reaction column and a price is reached that is three or more points below the last price recorded in the Natural Reaction column (with red lines underneath), then that price should be entered in red ink in the Downward Trend column."_

**Formal Spec:**

| Field           | Value                                                |
| --------------- | ---------------------------------------------------- |
| Precondition    | Currently recording in `NREAC`                                      |
| Pivot reference | Last pivotal point in `NREAC` with `underline="red"`                |
| Condition       | `price <= pivot_NREAC_red.price - confirm`                          |
| Action          | Record price in `DT` (red ink)                                      |
| Meaning         | **Downward trend confirmed — reversing from uptrend or resuming**   |

***

### Rule 6(a) — Transition: Upward Trend → Natural Reaction

> _"When a reaction occurs to an extent of approximately six points, after you have been recording prices in the Upward Trend column, you then start to record those prices in the Natural Reaction column, and continue to do so every day thereafter that the stock sells at a price which is lower than the last recorded price in the Natural Reaction column."_

**Formal Spec:**

| Field        | Value                                                        |
| ------------ | ------------------------------------------------------------ |
| Precondition | `current == UT`                                              |
| Condition    | `last[UT] - price >= swing`                                  |
| Action       | Record price in `NREAC` (pencil); trigger Rule 4(a)          |
| Continuation | Continue recording in `NREAC` whenever `price < last[NREAC]` |

***

### Rule 6(b) — Transition: Natural Rally → Natural Reaction (with DT override)

> _"When a reaction occurs to an extent of approximately six points, after you have been recording prices in the Natural Rally column, you then start to record those prices in the Natural Reaction column, and continue to do so every day thereafter that the stock sells at a price which is lower than the last recorded price in the Natural Reaction column. In case a price is made which is lower than the last recorded price in the Downward Trend column, you would then record that price in the Downward Trend column."_

**Formal Spec:**

| Field             | Value                                               |
| ----------------- | --------------------------------------------------- |
| Precondition      | `current == NR`                                     |
| Condition         | `last[NR] - price >= swing`                         |
| Action (primary)  | Record price in `NREAC`; trigger Rule 4(d)          |
| Action (override) | If `price < last[DT]` → record in `DT` instead      |
| Continuation      | In `NREAC`: keep recording if `price < last[NREAC]` |

***

### Rule 6(c) — Transition: Downward Trend → Natural Rally

> _"When a rally occurs to an extent of approximately six points, after you have been recording prices in the Downward Trend column, you then start to record those prices in the Natural Rally column, and continue to do so every day thereafter that the stock sells at a price which is higher than the last recorded price in the Natural Rally column."_

**Formal Spec:**

| Field        | Value                                                  |
| ------------ | ------------------------------------------------------ |
| Precondition | `current == DT`                                        |
| Condition    | `price - last[DT] >= swing`                            |
| Action       | Record price in `NR` (pencil); trigger Rule 4(c)       |
| Continuation | Continue recording in `NR` whenever `price > last[NR]` |

***

### Rule 6(d) — Transition: Natural Reaction → Natural Rally (with UT override)

> _"When a rally occurs to an extent of approximately six points, after you have been recording prices in the Natural Reaction column, you then start to record those prices in the Natural Rally column, and continue to do so every day thereafter that the stock sells at a price which is higher than the last recorded price in the Natural Rally column. In case a price is made which is higher than the last recorded price in the Upward Trend column, you would then record that price in the Upward Trend column."_

**Formal Spec:**

| Field             | Value                                          |
| ----------------- | ---------------------------------------------- |
| Precondition      | `current == NREAC`                             |
| Condition         | `price - last[NREAC] >= swing`                 |
| Action (primary)  | Record price in `NR`; trigger Rule 4(b)        |
| Action (override) | If `price > last[UT]` → record in `UT` instead |
| Continuation      | In `NR`: keep recording if `price > last[NR]`  |

***

### Rule 6(e) — Direct Override: Natural Reaction → Downward Trend

> _"When you start to record figures in the Natural Reaction column and a price is reached that is lower than the last recorded figure in the Downward Trend column — then that price should be entered in red ink in the Downward Trend column."_

**Formal Spec:**

| Field        | Value                                                                   |
| ------------ | ----------------------------------------------------------------------- |
| Precondition | `current == NREAC`                                                      |
| Condition    | `last[DT] is not None and price < last[DT]`                            |
| Action       | Record price in `DT` (red ink)                                          |
| Priority     | **Checked before swing-based transitions** (highest priority in NREAC)  |

***

### Rule 6(f) — Direct Override: Natural Rally → Upward Trend

> _"The same rule applies when you are recording figures in the Natural Rally column and a price is reached that is higher than the last price recorded in the Upward Trend column — then you would cease recording in the Natural Rally column and record that price in black ink in the Upward Trend column."_

**Formal Spec:**

| Field        | Value                                                                |
| ------------ | -------------------------------------------------------------------- |
| Precondition | `current == NR`                                                      |
| Condition    | `last[UT] is not None and price > last[UT]`                         |
| Action       | Record price in `UT` (black ink)                                     |
| Priority     | **Checked before swing-based transitions** (highest priority in NR)  |

***

### Rule 6(g) — Secondary Rally (indecisive upward move)

> _"In case you had been recording in the Natural Reaction column and a rally should occur of approximately six points from the last recorded figure in the Natural Reaction column — but that price did not exceed the last price recorded in the Natural Rally column — that price should be recorded in the Secondary Rally column and should continue to be so recorded until a price had been made which exceeded the last figure recorded in the Natural Rally column. When that occurs, you should commence to record prices in the Natural Rally column once again."_

**Formal Spec:**

| Field          | Value                                                          |
| -------------- | -------------------------------------------------------------- |
| Precondition   | `current == NREAC`, rally of `>= swing`                        |
| Condition      | `price <= last[NR]` ("did not exceed" = `<=`)                  |
| Action         | Record price in `SR` (pencil)                                  |
| Exit condition | `price > last[NR]` → promote to `NR`                           |
| Meaning        | **Market rallied but lacks conviction — watching and waiting** |

***

### Rule 6(h) — Secondary Reaction (indecisive downward move)

> _"In case you have been recording in the Natural Rally column and a reaction should occur of approximately six points, but the price reached on that reaction was not lower than the last recorded figure in your Natural Reaction column — that price should be entered in your Secondary Reaction column, and you should continue to record prices in that column until a price was made that was lower than the last price recorded in the Natural Reaction column. When that occurs, you should commence to record prices in the Natural Reaction column once again."_

**Formal Spec:**

| Field          | Value                                                                  |
| -------------- | ---------------------------------------------------------------------- |
| Precondition   | `current == NR`, reaction of `>= swing`                                |
| Condition      | `price >= last[NREAC]` ("not lower than" = `>=`)                       |
| Action         | Record price in `SREAC` (pencil)                                       |
| Exit condition | `price < last[NREAC]` → demote to `NREAC`                              |
| Meaning        | **Market reacted but selling pressure is weak — watching and waiting** |

***

### Rule 7 — Key Price Adjustment

> _"The same rules apply when recording the Key Price — except that you use twelve points as a basis instead of six points used in individual stocks."_

**Formal Spec:**

| Mode                  | swing     | confirm  |
| --------------------- | --------- | -------- |
| **Individual stock**  | 6 points  | 3 points |
| **Key Price (index)** | 12 points | 6 points |

***

### Rule 8 — Pivotal Point Formation

> _"The last price recorded in the Downward or Upward Trend columns becomes a Pivotal Point as soon as you begin to record prices in the Natural Rally or Natural Reaction columns. After a rally or reaction has ended, you start to record again in the reverse column, and the extreme price made in the previous column then becomes another Pivotal Point."_
>
> _"It is after two Pivotal Points have been reached that these records become of great value to you in helping you anticipate correctly the next movement of importance."_
>
> _"These Pivotal Points are drawn to your attention by having a double line drawn underneath them in either red ink or black ink. Those lines are drawn for the express purpose of keeping those points before you, and should be watched very carefully whenever prices are made and recorded near or at one of those points. Your decision to act will then depend on how prices are recorded from then on."_

**Formal Spec:**

This is the **meta-rule** that unifies Rules 4(a)–4(d). It establishes:

1. **Every column departure creates a pivot** at the extreme price of the column being left
2. **Two pivots form a decision bracket** — upper (from UT/NR) and lower (from DT/NREAC)
3. **Pivots are visually marked** with double underlines to force the trader's attention
4. **Action depends on price behavior at the pivot** — not on prediction

***

### Rule 9(a) — Buy Signal Near DT Pivot

> _"When you see black lines drawn below the last recorded red-ink figure in the Downward Trend column — you may be given a signal to buy near that point."_

**Formal Spec:**

| Field          | Value                                                                                   |
| -------------- | --------------------------------------------------------------------------------------- |
| Condition      | DT column has a pivot with `underline="black"`                                          |
| Interpretation | Price approaching this level from above during a rally → potential trend reversal point |
| Signal         | **Potential BUY** — watch for confirmation via Rule 10(d)                               |

***

### Rule 9(b) — Strength Test at NR Pivot

> _"When black lines are drawn below a price recorded in the Natural Rally column, and if the stock on its next rally reaches a point near that Pivotal Point price, that is the time you are going to find out whether the market is strong enough definitely to change its course into the Upward Trend column."_

**Formal Spec:**

| Field          | Value                                                                             |
| -------------- | --------------------------------------------------------------------------------- |
| Condition      | NR column has a pivot with `underline="black"`                                    |
| Interpretation | Price re-approaching this level tests whether bulls can overcome prior resistance |
| Signal         | **Strength test** — resolved by Rule 5(a) or Rule 10(e)                           |

***

### Rule 9(c) — Mirror of 9(a) and 9(b) for Bearish Side

> _"The reverse holds true when you see red lines drawn under the last price recorded in the Upward Trend column, and when red lines are drawn below the last price recorded in the Natural Reaction column."_

**Formal Spec:**

| Bullish equivalent                        | Bearish application                 |
| ----------------------------------------- | ----------------------------------- |
| Rule 9(a): black under DT → buy signal    | **Red under UT → sell signal**      |
| Rule 9(b): black under NR → strength test | **Red under NREAC → weakness test** |

***

### Rule 10(a) — Trend Resumption (both directions)

> _"This whole method is designed to enable one to see clearly whether a stock is acting the way it ought to, after its first Natural Rally or Reaction has occurred. If the movement is going to be resumed in a positive manner — either up or down — it will carry through its previous Pivotal Point — in individual stocks by three points, or, in the Key Price by six points."_

**Formal Spec:**

| Direction    | Condition                                                        | Signal                      |
| ------------ | ---------------------------------------------------------------- | --------------------------- |
| **Upward**   | `price >= UT_pivot(red).price + confirm` while recording in UT   | **BUY — uptrend resumed**   |
| **Downward** | `price <= DT_pivot(black).price - confirm` while recording in DT | **SELL — downtrend resumed** |

***

### Rule 10(b) — Upward Trend Failure

> _"If the stock fails to do this — and in a reaction sells three points or more below the last Pivotal Point (recorded in the Upward Trend column with red lines drawn underneath), it would indicate that the Upward Trend in the stock is over."_

**Formal Spec:**

| Field     | Value                                                   |
| --------- | ------------------------------------------------------- |
| Pivot     | UT pivot with `underline="red"`                         |
| Condition | `price <= pivot.price - confirm` (while in NREAC or DT) |
| Signal    | **SELL — uptrend is over**                              |

***

### Rule 10(c) — Downward Trend Resumption

> _"Applying the rule to the Downward Trend: Whenever, after a Natural Rally has ended, new prices are being recorded in the Downward Trend column, these new prices must extend three or more points below the last Pivotal Point (with black lines underneath), if the Downward Trend is to be positively resumed."_

**Formal Spec:**

| Field     | Value                                                  |
| --------- | ------------------------------------------------------ |
| Pivot     | DT pivot with `underline="black"`                      |
| Condition | `price <= pivot.price - confirm` while recording in DT |
| Signal    | **SELL — downtrend resumed**                           |

***

### Rule 10(d) — Downward Trend Failure

> _"If the stock fails to do this, and on a rally sells three or more points above the last Pivotal Point (recorded in the Downward Trend column with black lines drawn underneath), it would indicate that the Downward Trend in the stock is over."_

**Formal Spec:**

| Field     | Value                                                |
| --------- | ---------------------------------------------------- |
| Pivot     | DT pivot with `underline="black"`                    |
| Condition | `price >= pivot.price + confirm` (while in NR or UT) |
| Signal    | **BUY — downtrend is over**                          |

***

### Rule 10(e) — Danger Signal: Upward Trend Over

> _"When recording in the Natural Rally column, if the rally ends a short distance below the last Pivotal Point in the Upward Trend column (with red lines underneath), and the stock reacts three or more points from that price, it is a danger signal, which would indicate the Upward Trend in that stock is over."_

**Formal Spec:**

| Field       | Value                                                                    |
| ----------- | ------------------------------------------------------------------------ |
| Pivot       | UT pivot with `underline="red"`                                          |
| Condition 1 | NR peak is **close to but below** `pivot.price` (gap <= `confirm`)       |
| Condition 2 | Subsequent reaction of `>= confirm` points from that NR peak             |
| Signal      | **DANGER — uptrend may be over (bulls couldn't reclaim the high)**       |

***

### Rule 10(f) — Danger Signal: Downward Trend Over

> _"When recording in the Natural Reaction column, if the reaction ends a short distance above the last Pivotal Point in the Downward Trend column (with black lines underneath), and the stock rallies three or more points from that price, it is a danger signal, which would indicate the Downward Trend in that stock is over."_

**Formal Spec:**

| Field       | Value                                                                  |
| ----------- | ---------------------------------------------------------------------- |
| Pivot       | DT pivot with `underline="black"`                                      |
| Condition 1 | NREAC trough is **close to but above** `pivot.price` (gap <= `confirm`) |
| Condition 2 | Subsequent rally of `>= confirm` points from that NREAC trough         |
| Signal      | **DANGER — downtrend may be over (bears couldn't break the low)**      |

***

## Part II: Complete Rules → Code Traceability Matrix

Every rule maps to **exactly one primary code location**. All handlers are pure functions operating on immutable `EngineState`.

| Rule       | Primary Code Location        | Function / Property                             | Effect                        |
| ---------- | ---------------------------- | ----------------------------------------------- | ----------------------------- |
| **R1**     | `models.Col.ink`             | `@property` returns `"black"` for `UT`          | None                          |
| **R2**     | `models.Col.ink`             | `@property` returns `"red"` for `DT`            | None                          |
| **R3**     | `models.Col.ink`             | `@property` returns `"pencil"` for others       | None                          |
| **R4(a)**  | `engine._from_ut()`          | `_mark_pivot(state, UT, "red")`                 | New state with pivot appended |
| **R4(b)**  | `engine._from_nreac()`       | `_mark_pivot(state, NREAC, "red")`              | New state with pivot appended |
| **R4(c)**  | `engine._from_dt()`          | `_mark_pivot(state, DT, "black")`               | New state with pivot appended |
| **R4(d)**  | `engine._from_nr()`          | `_mark_pivot(state, NR, "black")`               | New state with pivot appended |
| **R5(a)**  | `engine._from_nr()`          | Priority 2 check                                | New state in `UT`             |
| **R5(b)**  | `engine._from_nreac()`       | Priority 2 check                                | New state in `DT`             |
| **R6(a)**  | `engine._from_ut()`          | Swing check                                     | New state in `NREAC`          |
| **R6(b)**  | `engine._from_nr()`          | Priority 3 + sub-branches                       | New state in `NREAC`/`DT`    |
| **R6(c)**  | `engine._from_dt()`          | Swing check                                     | New state in `NR`             |
| **R6(d)**  | `engine._from_nreac()`       | Priority 3 + sub-branches                       | New state in `NR`/`UT`       |
| **R6(e)**  | `engine._from_nreac()`       | Priority 1 (highest)                            | New state in `DT`             |
| **R6(f)**  | `engine._from_nr()`          | Priority 1 (highest)                            | New state in `UT`             |
| **R6(g)**  | `engine._from_nreac()`       | Priority 3c sub-branch                          | New state in `SR`             |
| **R6(h)**  | `engine._from_nr()`          | Priority 3c sub-branch                          | New state in `SREAC`          |
| **R7**     | `models.EngineConfig`        | `swing=12, confirm=6` for Key Price             | Config only                   |
| **R8**     | `engine._mark_pivot()`       | Called by R4(a-d) handlers                       | New state with pivot appended |
| **R9(a)**  | `engine._check_signals()`    | DT black pivot proximity                        | Potential BUY                 |
| **R9(b)**  | `engine._check_signals()`    | NR black pivot proximity                        | Strength test                 |
| **R9(c)**  | `engine._check_signals()`    | Mirror of 9(a)(b) for bearish                   | Potential SELL                |
| **R10(a)** | `engine._check_10a()`        | UT: `price >= pivot + confirm`                  | **BUY signal**                |
| **R10(b)** | `engine._check_10b()`        | NREAC/DT: `price <= UT_pivot - confirm`         | **SELL signal**               |
| **R10(c)** | `engine._check_10c()`        | DT: `price <= pivot - confirm`                  | **SELL signal**               |
| **R10(d)** | `engine._check_10d()`        | NR/UT: `price >= DT_pivot + confirm`            | **BUY signal**                |
| **R10(e)** | `engine._check_10e()`        | NR peak near UT pivot + react `>= confirm`      | **DANGER**                    |
| **R10(f)** | `engine._check_10f()`        | NREAC trough near DT pivot + rally `>= confirm` | **DANGER**                    |

***

## Part III: Project Structure

```
src/lafmm/
├── __init__.py     — Public re-exports
├── models.py       — Domain types (zero deps, all frozen)
├── engine.py       — Pure FSM functions (depends only on models)
├── group.py        — Group/market orchestration (depends on engine + models)
├── loader.py       — Filesystem I/O: reads group.toml + CSVs (depends on group + models)
├── app.py          — Interactive Textual TUI (depends on group + models)
├── tui.py          — Static Rich renderer for library/scripting use
└── main.py         — CLI entry point: folder → app
```

### Dependency Graph (strictly unidirectional)

```
main.py ──→ loader.py ──→ group.py ──→ engine.py ──→ models.py
   │                         │                          ↑
   └──→ app.py ──────────────┘──────────────────────────┘
```

Pure logic at the core (`models`, `engine`). Orchestration in the middle (`group`). I/O and presentation at the edges (`loader`, `app`, `main`).

### Data Layout (user-maintained)

```
data/
├── semis/
│   ├── group.toml        # name, leaders, thresholds
│   ├── NVDA/              # each ticker is a directory
│   │   └── 2026.csv       # year-partitioned OHLCV
│   ├── AVGO/
│   │   └── 2026.csv
│   └── AMD/               # tracked (auto-discovered)
│       └── 2026.csv
├── energy/
│   ├── group.toml
│   ├── XOM/
│   │   └── 2026.csv
│   └── CVX/
│       └── 2026.csv
```

***

## Part IV: Domain Types (`models.py`)

All types are `frozen=True, slots=True`. No mutation anywhere.

### Engine Types

| Type | Fields | Purpose |
|------|--------|---------|
| `Col` | Enum (SR, NR, UT, DT, NREAC, SREAC) | The six columns. Properties: `ink`, `is_bullish`, `is_bearish`, `label`, `short` |
| `SignalType` | Enum (BUY, SELL, DANGER_UP_OVER, DANGER_DOWN_OVER) | Trading signal classification |
| `Entry` | date, price, col | One row in the recording sheet |
| `PivotalPoint` | date, price, source_col, underline | A price with red or black underline |
| `Signal` | date, signal_type, price, rule, detail, pivot_ref | Advisory trading signal |
| `EngineConfig` | swing, confirm, ticker | Thresholds. Factories: `for_stock()`, `for_key_price()`, `for_stock_pct()` |
| `EngineState` | current, last, last_pivot, nr_peak, nreac_trough, entries, pivots, signals, emitted_keys | Complete immutable FSM state |

### Group Types

| Type | Fields | Purpose |
|------|--------|---------|
| `GroupTrend` | `Literal["bullish", "bearish", "neutral"]` | Group/market trend status |
| `GroupConfig` | name, leaders (2 tickers), swing_pct, confirm_pct, start_col | Group configuration from `group.toml` |
| `StockState` | ticker, config, engine (EngineState), is_leader | One stock's engine wrapped with its config |
| `GroupState` | config, key_price (StockState), stocks (tuple of StockState) | Complete group: leaders + Key Price engine + tracked stocks |
| `MarketState` | groups (tuple of GroupState) | All groups |

### Key Design Choices

- `EngineConfig.for_stock_pct(ticker, price, swing_pct)` converts percentage thresholds to absolute points from the stock's starting price
- `EngineState.last` and `EngineState.last_pivot` use `dict` for construction, conceptually immutable — new dicts created via `{**old, key: val}` on each transition
- Append-only collections use tuples: `(*old, new)` to extend
- Signal dedup uses `frozenset[tuple[str, str | None]]` — `(rule, pivot_key)` pairs

***

## Part V: Pure Functional Engine (`engine.py`)

### Design Principles

| Principle | Application |
|-----------|-------------|
| **Pure functions** | Every function: `(EngineState, ...) -> EngineState`. No `self`, no mutation. |
| **`match/case` dispatch** | `process()` dispatches to `_from_ut`, `_from_dt`, etc. via structural pattern matching |
| **Priority-ordered checks** | Each handler: direct override → pivot confirmation → swing transition → continuation |
| **Separate signal pass** | `_check_signals()` runs AFTER every state transition — cross-cutting, not embedded in handlers |
| **Signal dedup** | Normal signals: `(rule, pivot_key)`. Danger signals (10e/10f): `(rule, "NR_peak_{price}")` |

### Public API

- `start(col, date, price) -> EngineState` — initialize with UT or DT
- `process(state, cfg, date, price) -> EngineState` — feed one day's closing price

### Handler Priority Tables

See Part II traceability matrix for rule-to-handler mapping. Priority order within each handler:

| Handler | Priority 1 | Priority 2 | Priority 3 | Priority 4 |
|---------|-----------|-----------|-----------|-----------|
| `_from_ut` | Swing → NREAC (6a) | Continuation | — | — |
| `_from_dt` | Swing → NR (6c) | Continuation | — | — |
| `_from_nr` | Direct UT override (6f) | Pivot confirm → UT (5a) | Swing leave: DT/NREAC/SREAC (6b,6h) | Continuation |
| `_from_nreac` | Direct DT override (6e) | Pivot confirm → DT (5b) | Swing leave: UT/NR/SR (6d,6g) | Continuation |
| `_from_sr` | Exceed UT → UT directly | Exceed NR → NR (6g) | Swing → NREAC/DT | Continuation |
| `_from_sreac` | Below DT → DT directly | Below NREAC → NREAC (6h) | Swing → NR/UT | Continuation |

### Signal Checks (after every transition)

| Order | Rule | Signal | Condition |
|-------|------|--------|-----------|
| 1 | 10(a) | BUY | In UT, price >= UT pivot (red) + confirm |
| 2 | 10(c) | SELL | In DT, price <= DT pivot (black) - confirm |
| 3 | 10(b) | SELL | In NREAC/DT, price <= UT pivot (red) - confirm |
| 4 | 10(d) | BUY | In NR/UT, price >= DT pivot (black) + confirm |
| 5 | 10(e) | DANGER | NR peak near but below UT pivot, then reacted >= confirm |
| 6 | 10(f) | DANGER | NREAC trough near but above DT pivot, then rallied >= confirm |

***

## Part VI: Group & Market Layer (`group.py`)

### The 18-Column Map

Livermore tracked groups — two leader stocks per industry. Each group produces three 6-column engines:

| Engine | Input | Thresholds | Purpose |
|--------|-------|-----------|---------|
| Leader A | Stock A daily price | `swing_pct` of starting price | Individual stock trend |
| Leader B | Stock B daily price | `swing_pct` of starting price | Individual stock trend |
| **Key Price** | **A price + B price** | **swing=12, confirm=6** (Rule 7) | **Group trend confirmation** |

The **group trend** is determined solely by the Key Price engine's current column:
- Key Price in UT → group is **bullish**
- Key Price in DT → group is **bearish**
- Otherwise → **neutral**

### Tracked Stocks

Any CSV in a group folder that doesn't match a leader name is auto-discovered as a **tracked stock**. Tracked stocks run their own engine but do not affect the Key Price or group trend.

### Market Trend

Aggregated across all groups. >60% bullish → market bullish. >60% bearish → market bearish. Otherwise neutral.

### Pure Functions

- `group_leaders(state) -> (StockState, StockState)` — the two leaders
- `group_tracked(state) -> tuple[StockState, ...]` — non-leader stocks
- `group_trend(state) -> GroupTrend` — from Key Price column
- `market_trend(state) -> GroupTrend` — 60% threshold across groups
- `init_group(config, prices) -> GroupState` — initializes all engines from price data
- `process_group(state, date, prices) -> GroupState` — feeds one day to all engines
- `process_market(state, date, prices) -> MarketState` — feeds all groups

***

## Part VII: Interactive TUI (`app.py`)

Built on **Textual** (from the Rich ecosystem). Three-level drill-down:

| Screen | Shows | Navigation |
|--------|-------|------------|
| **DashboardScreen** | All groups: leaders, Key Price state, trend, tracked count | `Enter` → group, `q` → quit |
| **GroupScreen** | 18-column Livermore Map + signals + tracked stocks list | `Esc` → back, `Enter` → tracked stock, `q` → quit |
| **StockScreen** | Individual tracked stock's 6-column sheet + pivots + signals | `Esc` → back, `q` → quit |

### Visual Mapping (Livermore → Terminal)

| Livermore | Terminal | CSS/Style |
|-----------|----------|-----------|
| Black ink (UT) | **Bold green** | `bold green` |
| Red ink (DT) | **Bold red** | `bold red` |
| Pencil (others) | **Dim gray** | `dim` |
| Red underline pivot | **Red underline** | `underline red` |
| Black underline pivot | **White underline** | `underline bright_white` |

### Static Renderer (`tui.py`)

`tui.py` provides `render_sheet()` and `render_group_sheet()` for non-interactive use (library, scripting, piping). Uses Rich tables directly to stdout.

***

## Part VIII: Data Loading (`loader.py`)

I/O lives at the edge. Pure logic at the core.

- `load_prices(ticker_dir) -> list[tuple[str, float]]` — reads all year-partitioned OHLCV CSVs in a ticker directory, extracts `close` column, concatenates chronologically
- `load_group(folder) -> GroupState` — reads `group.toml` + all CSVs, initializes engines
- `load_market(root) -> MarketState` — scans subdirectories for group folders

### `group.toml` Format

```toml
name = "Semiconductors"         # display name
leaders = ["NVDA", "AVGO"]      # exactly 2, match CSV filenames
swing_pct = 5.0                 # swing as % of starting price (default: 5.0)
confirm_pct = 2.5               # confirm as % (default: 2.5)
start_col = "UT"                # initial trend: "UT" or "DT" (default: "UT")
```

***

## Part IX: Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Pure functions over engine class** | `(EngineState, ...) -> EngineState`. No `self`, no mutation. Old states preserved — debugging is time-travel. |
| **`frozen=True` on everything** | Livermore's records are ink on paper. All types immutable. `replace()` creates new, never mutates. |
| **Three engines per group** | Leader A + Leader B + Key Price. Key Price = combined price with doubled thresholds (Rule 7). Group trend from Key Price only. |
| **Folder-as-group convention** | No database, no config files beyond `group.toml`. Filesystem IS the data model. Drop a CSV, it's tracked. |
| **Percentage-based thresholds** | Modern stocks range $55-$950. Fixed 6-point swings meaningless. `swing_pct` converts to absolute points from starting price. |
| **Leader vs tracked** | Leaders form Key Price. Tracked stocks run independently for reference but don't affect group trend. Auto-discovered from folder. |
| **Market trend = 60% consensus** | Livermore looked at majority of groups agreeing. 60% threshold balances conviction vs noise. |
| **Textual for interactive TUI** | Same ecosystem as Rich. Three-level drill-down mirrors the three-level analysis: market → group → stock. |
| **`tui.py` kept as static renderer** | Library/scripting use. Not everyone needs an interactive app. |
| **`match/case` for dispatch** | Structural pattern matching on `Col` enum — exhaustive, readable, Pythonic. |
| **Signal dedup via `frozenset`** | `(rule, pivot_key)` tuples prevent duplicate emissions without mutable sets. |
| **No `Any` anywhere** | Every type explicit. `Literal` for constrained strings, generics for containers. |

***

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."*
— Antoine de Saint-Exupery

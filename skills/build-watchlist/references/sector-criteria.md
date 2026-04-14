# Sector Evaluation & Leader Selection

## What makes a good leader

Livermore always tracked the two strongest names in each industry group.
The Key Price — the combined daily price of both leaders — gives the
definitive group trend. Wrong leaders produce a misleading Key Price,
which makes the entire group analysis unreliable.

### The five criteria

**1. Liquidity**

The stock must trade enough daily volume that its closing price is
meaningful — not pushed around by a few large orders. As a rule of
thumb, average daily dollar volume above $500M is comfortable. Below
$100M is risky for leader status.

Why this matters: the Livermore engine records closing prices. If the
close is noisy because volume is thin, the engine will see false
extremes and record entries that don't reflect genuine supply/demand.

**2. Market cap dominance**

Leaders should be among the largest companies in the sector by market
cap. Livermore traded the biggest names — US Steel, Bethlehem Steel,
General Motors. The modern equivalent: NVDA not MRVL, XOM not DVN,
JPM not ZION.

Large caps are harder to manipulate, more liquid, and more likely to
represent the sector's true direction rather than idiosyncratic events.

**3. Sector representativeness**

The stock should move because of sector forces, not just company-specific
events. A good test: when the sector has a broad up or down day, does
this stock participate? If it frequently diverges from its sector peers
for company-specific reasons (lawsuits, one-off contracts), it may be a
poor sector proxy.

**4. Correlation without redundancy**

The two leaders should be correlated (they track the same sector) but
not redundant (they capture different facets of the sector). Ideal: two
companies in the same sector but different sub-sectors.

When `quant/correlation.py` is available, run `pairwise_correlation` on
two candidates' return series. Correlation between 0.5-0.85 is ideal —
high enough to represent the same sector, low enough to capture
different information. Until then, use the sub-sector test: same sector
but different end markets = good pair.

Examples of good pairs:
- **Semis**: NVDA (GPU/AI) + AVGO (networking/broadcom) — same sector,
  different end markets
- **Energy**: XOM (integrated major) + CVX (integrated major, different
  geographic mix) — or XOM + SLB (production vs services)
- **Financials**: JPM (universal bank) + GS (investment bank) — same
  sector, different business models

Examples of bad pairs:
- NVDA + AMD — too similar (both GPU-heavy), redundant signal
- XOM + OXY — OXY is too small relative to XOM, creates Key Price
  imbalance
- AAPL + MSFT — both are mega-caps but they represent "tech" too
  broadly; pick a narrower sector

**5. Price level compatibility**

The two leaders' prices are summed daily to form the Key Price. If one
stock is $800 and the other is $40, the cheaper stock has almost no
influence on the Key Price — it's effectively a single-stock analysis.

Ideal: both leaders within the same order of magnitude. $100-$200 range
for both is fine. $800 + $40 is a problem. If the best two leaders have
a large price gap, it doesn't disqualify them — just be aware that the
Key Price will be dominated by the higher-priced stock.

## When to add a sector

A sector is worth tracking when at least one of these is true:

- **Active catalysts** — earnings season, regulatory decisions, macro
  shifts affecting the sector. Use news-context to assess.
- **The user trades it** — if their journal shows activity in un-tracked
  sectors, those sectors should be tracked for signal alignment analysis.
- **Portfolio diversification** — the user's profile says they want
  sector diversity but all their groups are tech-adjacent. Add a
  non-correlated sector (energy, healthcare, financials).
- **Livermore's principle** — track sectors in quiet periods too. You
  want to see the column transition when the trend starts, not after
  it's already established. Being early is the whole point.

There is no minimum number of sectors. One well-chosen sector with good
leaders beats five poorly chosen ones.

## When NOT to add a sector

- **No liquid leaders** — if the sector's largest stocks trade under
  $100M daily volume, the closing prices will be too noisy for the
  engine.
- **Too many groups already** — check the user's profile for
  concentration limits. More groups means more maintenance (daily price
  updates, more signals to review). If the user has 8+ groups, adding
  another dilutes attention.
- **Redundant with existing groups** — adding a "cloud computing" group
  when you already have "software" is likely redundant. The leaders would
  overlap or correlate heavily. Use the correlation analysis (future
  quant skill) to test this.

## Sector catalog

This catalog is a starting point, not an authority. Market structure
changes. Leaders rotate. Always verify the five criteria against current
data before selecting leaders.

If a suggested leader's average daily dollar volume has dropped below
$200M, or if a new company has emerged as the sector's dominant force,
the catalog entry is stale. Use the news-context skill to research
current sector leaders and apply the five criteria fresh.

| Sector | Sub-sectors | Example leaders | Notes |
|--------|------------|-----------------|-------|
| Semiconductors | GPU/AI, networking, memory, equipment | NVDA + AVGO, or NVDA + ASML | Highest vol sector in recent years |
| Software | Enterprise, cloud, cybersecurity | MSFT + CRM, or MSFT + ORCL | MSFT dominates; pair with a pure-play |
| Internet/Media | Search, social, e-commerce | GOOGL + META, or AMZN + META | AMZN straddles retail + cloud |
| Energy (Oil/Gas) | Integrated, E&P, services | XOM + CVX, or XOM + SLB | Geopolitical sensitivity |
| Energy (Uranium) | Miners, enrichment | CCJ + UEC, or CCJ + LEU | Smaller sector, lower liquidity |
| Financials (Banks) | Universal, investment, regional | JPM + GS, or JPM + BAC | Rate-sensitive |
| Financials (Insurance) | P&C, life, reinsurance | BRK.B + PGR | Less correlated with banks |
| Healthcare (Pharma) | Big pharma, biotech | LLY + JNJ, or LLY + ABBV | LLY has dominated recently |
| Healthcare (Biotech) | Large-cap biotech | AMGN + GILD, or AMGN + REGN | FDA binary events |
| Consumer Discretionary | Retail, autos, luxury | AMZN + TSLA, or HD + MCD | TSLA is high-vol, choose carefully |
| Consumer Staples | Food, household, beverages | PG + KO, or PG + COST | Low vol, good for stability |
| Industrials | Aerospace, machinery, transport | CAT + DE, or BA + HON | Cyclical, capex-sensitive |
| Utilities | Electric, gas, water | NEE + SO, or NEE + DUK | Low vol, rate-sensitive |
| Real Estate | REITs | PLD + AMT, or PLD + EQIX | Rate-sensitive, sector ETF is XLRE |
| Materials | Metals, chemicals, mining | FCX + NEM, or LIN + APD | Commodity-driven |
| Telecom | Carriers, infrastructure | T + VZ | Low growth, dividend-focused |

**For sectors not listed:** use news-context + WebSearch to identify the
two highest-volume, highest-market-cap names. Verify they meet the five
criteria above.

## The scaffolding recipe

After selecting leaders (and optionally tracked stocks):

```
~/.lafmm/data/{group}/
├── group.toml              # name, leaders, thresholds
├── {LEADER_A}/             # ticker directory (created empty)
├── {LEADER_B}/
└── {TRACKED}/              # optional additional stocks
```

**group.toml format:**

```toml
name = "Semiconductors"
leaders = ["NVDA", "AVGO"]
swing_pct = 5.0
confirm_pct = 2.5
```

Start with `swing_pct = 5.0` and `confirm_pct = 2.5`. These are
placeholders — run tune-thresholds after fetching prices to calibrate
from actual volatility.

The engine discovers tracked stocks automatically — any ticker
directory that is not listed in `leaders` becomes a tracked stock with
its own engine. No registration needed.

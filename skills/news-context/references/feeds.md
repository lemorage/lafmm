# Curated Financial RSS Feeds

These feeds are a convenience — not a limit. Use any source that fits the
situation. These have been verified to return valid RSS/Atom XML via direct
HTTP fetch.

Many feeds below use Google News RSS as a proxy. This is intentional: the
underlying sources (Bloomberg, Reuters, MarketWatch) frequently block direct
RSS access from non-browser clients, but their articles are indexed and
available through Google News search RSS endpoints.

## Tier 1 — Primary (broad, reliable, high signal)

### Markets & Equities

| Name | URL |
|------|-----|
| CNBC Markets | `https://www.cnbc.com/id/100003114/device/rss/rss.html` |
| Yahoo Finance | `https://finance.yahoo.com/rss/topstories` |
| Yahoo Finance News | `https://finance.yahoo.com/news/rssindex` |
| Seeking Alpha | `https://seekingalpha.com/market_currents.xml` |
| Reuters Markets | `https://news.google.com/rss/search?q=site:reuters.com+markets+stocks+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Bloomberg Markets | `https://news.google.com/rss/search?q=site:bloomberg.com+markets+when:1d&hl=en-US&gl=US&ceid=US:en` |
| MarketWatch | `https://news.google.com/rss/search?q=site:marketwatch.com+markets+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Investing.com | `https://news.google.com/rss/search?q=site:investing.com+markets+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Wall Street Journal | `https://feeds.content.dowjones.io/public/rss/RSSUSnews` |

### Macro & Central Banks

| Name | URL |
|------|-----|
| Economic Data | `https://news.google.com/rss/search?q=(CPI+OR+inflation+OR+GDP+OR+"jobs+report"+OR+"nonfarm+payrolls"+OR+PMI)+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Reuters Business | `https://news.google.com/rss/search?q=site:reuters.com+business+markets&hl=en-US&gl=US&ceid=US:en` |
| Trade & Tariffs | `https://news.google.com/rss/search?q=(tariff+OR+"trade+war"+OR+"trade+deficit"+OR+sanctions)+when:2d&hl=en-US&gl=US&ceid=US:en` |

## Tier 2 — Domain-Specific

### Energy

| Name | URL |
|------|-----|
| Reuters Energy | `https://news.google.com/rss/search?q=site:reuters.com+(oil+OR+gas+OR+energy+OR+OPEC)+when:3d&hl=en-US&gl=US&ceid=US:en` |
| Oil & Gas | `https://news.google.com/rss/search?q=(oil+price+OR+"crude+oil"+OR+OPEC+OR+"natural+gas"+OR+"oil+supply")+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Nuclear Energy | `https://news.google.com/rss/search?q=("nuclear+energy"+OR+"nuclear+power"+OR+uranium+OR+IAEA)+when:3d&hl=en-US&gl=US&ceid=US:en` |

### Commodities & Metals

| Name | URL |
|------|-----|
| Bloomberg Commodities | `https://news.google.com/rss/search?q=site:bloomberg.com+commodities+OR+metals+OR+mining+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Reuters Commodities | `https://news.google.com/rss/search?q=site:reuters.com+commodities+OR+metals+OR+mining+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Gold | `https://news.google.com/rss/search?q=(gold+price+OR+"gold+market"+OR+bullion+OR+LBMA)+when:1d&hl=en-US&gl=US&ceid=US:en` |
| Copper | `https://news.google.com/rss/search?q=(copper+price+OR+"copper+market"+OR+"copper+supply"+OR+COMEX+copper)+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Iron Ore | `https://news.google.com/rss/search?q=("iron+ore"+price+OR+"iron+ore+market"+OR+"steel+raw+materials")+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Lithium | `https://news.google.com/rss/search?q=(lithium+price+OR+"lithium+market"+OR+"lithium+supply"+OR+spodumene+OR+LCE)+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Uranium | `https://news.google.com/rss/search?q=(uranium+price+OR+"uranium+market"+OR+U3O8+OR+nuclear+fuel)+when:3d&hl=en-US&gl=US&ceid=US:en` |
| Commodity Futures | `https://news.google.com/rss/search?q=(COMEX+OR+NYMEX+OR+"commodity+futures"+OR+CME+commodities)+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Commodity Trade Mantra | `https://www.commoditytrademantra.com/feed/` |

### Crypto

| Name | URL |
|------|-----|
| Crypto News | `https://news.google.com/rss/search?q=(bitcoin+OR+ethereum+OR+crypto+OR+"digital+assets")+when:1d&hl=en-US&gl=US&ceid=US:en` |
| CryptoSlate | `https://cryptoslate.com/feed/` |
| Unchained | `https://unchainedcrypto.com/feed/` |

### Fixed Income & FX

| Name | URL |
|------|-----|
| Bond Market | `https://news.google.com/rss/search?q=("bond+market"+OR+"treasury+yields"+OR+"bond+yields"+OR+"fixed+income")+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Forex | `https://news.google.com/rss/search?q=("forex"+OR+"currency"+OR+"FX+market")+trading+when:1d&hl=en-US&gl=US&ceid=US:en` |

### Supply Chain & Logistics

| Name | URL |
|------|-----|
| Shipping & Freight | `https://news.google.com/rss/search?q=("bulk+carrier"+OR+"dry+bulk"+OR+"commodity+shipping"+OR+"Port+Hedland"+OR+"Strait+of+Hormuz")+when:3d&hl=en-US&gl=US&ceid=US:en` |
| China Commodity Imports | `https://news.google.com/rss/search?q=(China+imports+copper+OR+iron+ore+OR+lithium+OR+cobalt+OR+"rare+earth")+when:3d&hl=en-US&gl=US&ceid=US:en` |

## Tier 3 — Supplementary

### Sentiment & Flow

| Name | URL |
|------|-----|
| Options Market | `https://news.google.com/rss/search?q=("options+market"+OR+"options+trading"+OR+"put+call+ratio"+OR+VIX)+when:2d&hl=en-US&gl=US&ceid=US:en` |
| Risk & Volatility | `https://news.google.com/rss/search?q=(VIX+OR+"market+volatility"+OR+"risk+off"+OR+"market+correction")+when:3d&hl=en-US&gl=US&ceid=US:en` |
| Market Outlook | `https://news.google.com/rss/search?q=("market+outlook"+OR+"stock+market+forecast"+OR+"bull+market"+OR+"bear+market")+when:3d&hl=en-US&gl=US&ceid=US:en` |
| Housing Market | `https://news.google.com/rss/search?q=("housing+market"+OR+"home+prices"+OR+"mortgage+rates"+OR+REIT)+when:3d&hl=en-US&gl=US&ceid=US:en` |

### Geopolitical (macro-relevant)

| Name | URL |
|------|-----|
| BBC World | `https://feeds.bbci.co.uk/news/world/rss.xml` |
| Reuters World | `https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en` |
| AP News | `https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en` |

## Constructing Sector-Specific Queries

For sectors not covered above, construct a Google News RSS query:

```
https://news.google.com/rss/search?q={QUERY}+when:{RECENCY}&hl=en-US&gl=US&ceid=US:en
```

**Parameters:**
- `{QUERY}` — URL-encoded search terms, use `+` for spaces, `OR` for alternatives, quotes for exact phrases
- `{RECENCY}` — `1d`, `2d`, `3d`, `7d`, `14d`, `30d`

**Examples:**
- Semiconductors: `q=(NVDA+OR+TSMC+OR+ASML+OR+"semiconductor")+when:2d`
- Biotech: `q=("FDA+approval"+OR+"clinical+trial"+OR+biotech+earnings)+when:3d`
- Software: `q=(SaaS+OR+"cloud+computing"+OR+"enterprise+software")+earnings+when:2d`

This pattern lets you target any sector, ticker, or theme without needing a
pre-curated feed.

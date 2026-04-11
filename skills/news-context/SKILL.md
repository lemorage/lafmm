---
name: news-context
description: >
  Fetch, filter, and classify financial news from RSS feeds and web search.
  Use this skill whenever you need current market news or context about price
  movements — whether you are building a watchlist and need to know which
  sectors have active catalysts, analyzing why a stock or sector moved
  unexpectedly, researching what macro events might impact a position,
  performing any market analysis that benefits from recent headlines, or the
  user asks about latest developments in a sector, commodity, or the broad
  market. Also use this when the user says things like "check the news",
  "what's happening with X", "why did Y drop", "what's moving today", "any
  news on...", "latest on...", "what's going on with...", "market update",
  "what should I know about...", or any variation that implies they want
  current financial information. Use it proactively when you judge that news
  context would improve the quality of your analysis — you do not need to
  be asked.
---

# News Context

This skill gives you the ability to gather and make sense of financial news.
You have two channels for gathering and a classification framework for
organizing what you find. Use as much or as little as the situation demands.

## Gathering news

You have two channels. Use whichever fits, or both.

### RSS feeds

`references/feeds.md` has curated financial RSS feed URLs organized by domain
(equities, macro, energy, commodities, crypto, fixed income, geopolitical).
Fetch any feed URL with `WebFetch`. The response is XML — extract `<title>`
and `<description>` from each `<item>` element.

These feeds are a starting point, not a boundary. If you know a better source
for the specific sector or topic, use it. The reference file also explains how
to construct custom Google News RSS queries for any ticker, sector, or theme
you need — so you can build a targeted feed on the fly.

**When RSS is the right choice:** Broad market scans, sector overviews,
systematic coverage of multiple domains at once. RSS gives you volume and
breadth efficiently.

### Web search

Use `WebSearch` for anything the curated feeds do not cover, or when you need
the very latest information. Good for: breaking news, niche sectors, specific
company events, verifying or deepening something you found in RSS.

**Constructing good queries:** Include the ticker or company name, the
specific event type, and a recency signal. "NVDA earnings guidance Q2 2026" is
better than "NVIDIA news". For macro topics, name the specific indicator:
"CPI April 2026" not "inflation news".

### Choosing your approach

For a broad market scan (many sectors, general briefing), start with RSS —
grab 2-3 tier-1 feeds from the reference file. For a targeted question about
one stock or event, go straight to WebSearch. For thorough analysis, do both:
RSS for systematic coverage, then WebSearch to fill gaps or chase specific
threads.

You are not required to use both. A single WebSearch might be all you need. A
single RSS feed might be enough. Match the effort to the question.

## Making sense of what you find

### The three-atom framework

`references/three-atoms.md` explains this in depth. The core idea: every
headline that moves prices affects one or more of three forces.

| Atom | Drives | Examples |
|------|--------|----------|
| **E[CF]** | Expected future cash flows | Earnings, guidance, demand shifts, new products, regulatory rulings |
| **r** | Discount rate | Fed decisions, inflation data, yield curve, credit spreads |
| **S/D** | Supply/demand for the security | Buybacks, insider trades, fund flows, index rebalancing, short interest |

Classifying headlines through this lens is useful because it turns a wall of
news into structured evidence. When you see five headlines all hitting the
same atom in the same direction, that is a signal. When two atoms conflict
(positive E[CF] but deteriorating r), that tension is worth surfacing.

This framework is a tool, not a requirement. If the user just wants a quick
summary of what is happening, a plain-language summary without atom tags may
be the right output. If they are doing deep analysis, the atom classification
adds real value. Read the situation.

### Connecting to other data

If you have access to Livermore state (in `~/.lafmm/cache/`), price data, or
other analytical context, connect the news to it. Some patterns to look for:

- **Convergence** — a trading signal and headlines both pointing the same
  direction on the same atom. This strengthens the signal's case.
- **Contradiction** — a signal says one thing, headlines say another. Surface
  the tension without resolving it. That judgment belongs to the human.
- **Cross-sector correlation** — multiple sectors moving together. If the
  headlines are all about the same atom (usually r), that explains the
  correlation. If not, dig deeper.
- **Rotation** — S/D atom headlines showing flows leaving one sector for
  another. Useful context for watchlist decisions.

But if you do not have Livermore state or any other data to connect to, the
news is still valuable on its own. Do not skip gathering just because there is
nothing to cross-reference against.

## Output

Adapt your output to what the user actually needs:

- **Quick briefing** — plain language, lead with the most important
  development, keep it short
- **Sector research** (e.g., for watchlist building) — organize by sector,
  highlight active catalysts and risks, note which sectors have the most
  activity
- **Diagnostic** ("why did X move?") — lead with the most likely explanation,
  cite the specific headline(s), classify by atom if it adds clarity
- **Deep analysis** — group by atom, note convergence or contradiction with
  any available data, flag multi-atom events

In all cases: present evidence, not predictions. Your job is to organize what
is happening into a clear picture. The human decides what to do about it.

## Examples

**Example 1: Watchlist research**

User: "I'm thinking about adding a biotech group. What's happening in that
sector right now?"

You would: WebSearch for recent biotech catalysts (FDA decisions, clinical
trial results, M&A), fetch the curated macro feeds to check if rate
environment favors growth stocks, and summarize: which companies have active
catalysts (E[CF]), whether the rate environment is favorable (r), and if
there are notable fund flows into/out of biotech ETFs (S/D).

**Example 2: Diagnostic**

User: "NVDA dropped 8% today, why?"

You would: WebSearch "NVDA stock drop today", check semiconductor and
broad market feeds, and report what you find — maybe it is an earnings miss
(E[CF]), maybe it is a broad market sell-off from a hot CPI print (r), maybe
it is an index rebalance (S/D), or some combination.

**Example 3: Proactive use during analysis**

You are analyzing a group and notice the Key Price just entered Natural
Reaction. Without being asked, you fetch relevant sector news to see if
headlines explain the shift. You find three articles about supply chain
disruptions (E[CF]) and one about institutional selling (S/D). You weave this
context into your analysis.

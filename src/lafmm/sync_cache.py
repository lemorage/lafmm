"""Regenerate ~/.lafmm/cache/ from data/.

Loads all groups via the engine, renders each as markdown, and writes
to cache/. The cache mirrors data/ — same group names, same tickers.

Usage from ~/.lafmm/ (agent context):
    $(cat .python) -m lafmm.sync_cache

Usage from project directory:
    uv run lafmm-sync

Usage as library:
    from lafmm.sync_cache import sync_market
    sync_market(data_dir, cache_dir)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lafmm.group import group_leaders, group_tracked, group_trend, market_trend
from lafmm.loader import load_market
from lafmm.models import (
    COL_ORDER,
    Entry,
    GroupState,
    MarketState,
    Signal,
    SignalType,
    StockState,
)

TREND_LABELS: dict[str, str] = {
    "bullish": "BULLISH",
    "bearish": "BEARISH",
    "neutral": "NEUTRAL",
}

SIGNAL_LABELS: dict[SignalType, str] = {
    SignalType.BUY: "BUY",
    SignalType.SELL: "SELL",
    SignalType.DANGER_UP_OVER: "DANGER: Up Over",
    SignalType.DANGER_DOWN_OVER: "DANGER: Dn Over",
}


# ── Markdown Renderers ──────────────────────────────────────────────


def _render_signal_line(s: Signal) -> str:
    label = SIGNAL_LABELS[s.signal_type]
    return f"- **{label}** ${s.price:.2f} Rule {s.rule} — {s.detail} ({s.date})"


def _col_label(stock: StockState) -> str:
    return stock.engine.current.short if stock.engine.current else "N/A"


def _kp_label(group: GroupState) -> str:
    kp = group.key_price
    if kp and kp.engine.current:
        return kp.engine.current.short
    return "N/A"


def _render_stock_md(stock: StockState) -> str:
    e = stock.engine
    latest = e.entries[-1].date if e.entries else "N/A"
    lines = [
        f"## {stock.ticker} — as of {latest}",
        "",
        f"**Column: {_col_label(stock)}**"
        f" | Swing: {stock.config.swing:.1f}"
        f" | Confirm: {stock.config.confirm:.1f}",
        "",
        "### Sheet Summary",
        f"{len(e.entries)} entries, {len(e.pivots)} pivotal points, {len(e.signals)} signals",
        "",
    ]

    if e.pivots:
        lines.append("### Active Pivots")
        lines.extend(
            f"- {p.date} {p.source_col.short} ${p.price:.2f} ({p.underline} underline)"
            for p in e.pivots
        )
        lines.append("")

    if e.signals:
        lines.append("### Active Signals")
        lines.extend(_render_signal_line(s) for s in e.signals)
        lines.append("")

    if e.entries:
        lines.append("### Sheet")
        header = "| Date | " + " | ".join(c.short for c in COL_ORDER) + " |"
        sep = "|------|" + "|".join("--------:" for _ in COL_ORDER) + "|"
        lines.append(header)
        lines.append(sep)
        for entry in e.entries:
            cells = [f"${entry.price:.2f}" if col is entry.col else "" for col in COL_ORDER]
            lines.append(f"| {entry.date} | " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines)


def _render_map_row(
    date: str,
    a_by_date: dict[str, Entry],
    b_by_date: dict[str, Entry],
    kp_by_date: dict[str, Entry],
) -> str:
    cells: list[str] = [date]
    for by_date in (a_by_date, b_by_date):
        entry = by_date.get(date)
        for col in COL_ORDER:
            if entry is not None and col is entry.col:
                cells.append(f"${entry.price:.2f}")
            else:
                cells.append("")
        cells.append("")
    entry = kp_by_date.get(date)
    for col in COL_ORDER:
        if entry is not None and col is entry.col:
            cells.append(f"${entry.price:.2f}")
        else:
            cells.append("")
    return "| " + " | ".join(cells) + " |"


def _render_group_md(group: GroupState) -> str:
    a, b = group_leaders(group)
    label = TREND_LABELS[group_trend(group)]

    lines = [
        f"## {group.config.name} — Key Price: {label}",
        "",
        "### Livermore Map",
        "",
    ]

    cols = [c.short for c in COL_ORDER]
    all_headers = [
        *[f"{a.ticker} {c}" for c in cols],
        "|",
        *[f"{b.ticker} {c}" for c in cols],
        "|",
        *[f"KEY {c}" for c in cols],
    ]
    header = "| Date | " + " | ".join(all_headers) + " |"
    sep_parts = ["------"]
    sep_parts.extend("--------:" for _ in cols)
    sep_parts.append("-")
    sep_parts.extend("--------:" for _ in cols)
    sep_parts.append("-")
    sep_parts.extend("--------:" for _ in cols)
    lines.append(header)
    lines.append("|" + "|".join(sep_parts) + "|")

    a_by_date = {e.date: e for e in a.engine.entries}
    b_by_date = {e.date: e for e in b.engine.entries}
    kp_by_date: dict[str, Entry] = {}
    if group.key_price:
        kp_by_date = {e.date: e for e in group.key_price.engine.entries}
    all_dates = sorted(a_by_date.keys() | b_by_date.keys() | kp_by_date.keys())

    for date in all_dates:
        lines.append(_render_map_row(date, a_by_date, b_by_date, kp_by_date))

    lines.append("")

    all_signals: list[Signal] = [*a.engine.signals, *b.engine.signals]
    if group.key_price:
        all_signals.extend(group.key_price.engine.signals)

    if all_signals:
        lines.append("### Signals")
        lines.extend(_render_signal_line(s) for s in all_signals)
        lines.append("")

    tracked = group_tracked(group)
    if tracked:
        lines.append("### Tracked Stocks")
        for stock in tracked:
            lines.append(f"- **{stock.ticker}**: {_col_label(stock)}")
        lines.append("")

    return "\n".join(lines)


def _render_market_row(g: GroupState) -> str:
    a, b = group_leaders(g)
    gt = group_trend(g)
    return (
        f"| {g.config.name} | {a.ticker} | {_col_label(a)}"
        f" | {b.ticker} | {_col_label(b)}"
        f" | {_kp_label(g)} | {TREND_LABELS[gt]} |"
    )


def _render_market_md(market: MarketState) -> str:
    label = TREND_LABELS[market_trend(market)]
    lines = [
        f"## Market Trend: {label}",
        "",
        "| Group | Leader A | A State | Leader B | B State | Key Price | Trend |",
        "|-------|----------|---------|----------|---------|-----------|-------|",
    ]
    lines.extend(_render_market_row(g) for g in market.groups)
    lines.append("")
    return "\n".join(lines)


# ── Sync Logic ──────────────────────────────────────────────────────


def sync_market(data_dir: Path, cache_dir: Path) -> int:
    market = load_market(data_dir)
    if not market.groups:
        print("no groups found in data/", file=sys.stderr)
        return 0

    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "market.md").write_text(_render_market_md(market))
    print("cache/market.md")

    count = 1
    for group in market.groups:
        group_cache = cache_dir / group.config.name.lower().replace(" ", "-")
        group_cache.mkdir(parents=True, exist_ok=True)

        (group_cache / "group.md").write_text(_render_group_md(group))
        print(f"cache/{group_cache.name}/group.md")
        count += 1

        for stock in group.stocks:
            (group_cache / f"{stock.ticker}.md").write_text(_render_stock_md(stock))
            print(f"cache/{group_cache.name}/{stock.ticker}.md")
            count += 1

    print(f"\nsynced {count} files")
    return count


# ── CLI Entry Point ─────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate LAFMM cache from data",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="path to data directory (default: ~/.lafmm/data)",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="path to cache directory (default: ~/.lafmm/cache)",
    )
    args = parser.parse_args()

    from lafmm.init import _lafmm_home

    root = _lafmm_home()
    data_dir = args.data or root / "data"
    cache_dir = args.cache or root / "cache"

    if not data_dir.exists():
        print(f"error: {data_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    sync_market(data_dir, cache_dir)

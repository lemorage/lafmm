from collections.abc import Sequence

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from lafmm.colors import NEGATIVE, NEUTRAL, POSITIVE
from lafmm.group import group_leaders, group_tracked, group_trend, market_trend
from lafmm.models import (
    COL_ORDER,
    Col,
    EngineConfig,
    EngineState,
    GroupState,
    GroupTrend,
    MarketState,
    PivotalPoint,
    Signal,
    SignalType,
    StockState,
)

INK_STYLES: dict[str, str] = {
    "black": f"bold {POSITIVE}",
    "red": f"bold {NEGATIVE}",
    "pencil": "dim",
}

SIGNAL_STYLES: dict[SignalType, tuple[str, str]] = {
    SignalType.BUY: (f"bold {POSITIVE}", "BUY"),
    SignalType.SELL: (f"bold {NEGATIVE}", "SELL"),
    SignalType.DANGER_UP_OVER: (f"bold {NEUTRAL}", "DANGER: Up Over"),
    SignalType.DANGER_DOWN_OVER: (f"bold {NEUTRAL}", "DANGER: Dn Over"),
}

TREND_STYLES: dict[GroupTrend, tuple[str, str]] = {
    "bullish": (f"bold {POSITIVE}", "BULLISH"),
    "bearish": (f"bold {NEGATIVE}", "BEARISH"),
    "neutral": (f"bold {NEUTRAL}", "NEUTRAL"),
}


# ── Single Stock Sheet ───────────────────────────────────────────────


def render_sheet(
    state: EngineState,
    cfg: EngineConfig,
    console: Console | None = None,
) -> None:
    con = console or Console()
    _render_main_table(state, cfg, con)
    if state.pivots:
        _render_pivot_table(state.pivots, con)
    if state.signals:
        _render_signal_table(state.signals, con)


def format_price(
    price: float,
    col: Col,
    pivots: Sequence[PivotalPoint],
) -> Text:
    style = INK_STYLES[col.ink]
    txt = Text(f"{price:>8.2f}", style=style)
    for pivot in pivots:
        if pivot.source_col is col and pivot.price == price:
            ul_color = "red" if pivot.underline == "red" else "bright_white"
            txt.stylize(f"underline {ul_color}")
            break
    return txt


def _render_main_table(
    state: EngineState,
    cfg: EngineConfig,
    console: Console,
) -> None:
    title = f"Livermore Market Key — {cfg.ticker}" if cfg.ticker else "Livermore Market Key"
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=True)
    table.add_column("Date", style="cyan", width=12)
    for col in COL_ORDER:
        table.add_column(col.short, justify="right", width=12)

    for entry in state.entries:
        row: list[Text | str] = [entry.date]
        for col in COL_ORDER:
            if col is entry.col:
                row.append(format_price(entry.price, col, state.pivots))
            else:
                row.append("")
        table.add_row(*row)

    console.print(table)


def _render_pivot_table(pivots: Sequence[PivotalPoint], console: Console) -> None:
    table = Table(title="Pivotal Points", box=box.ROUNDED)
    table.add_column("Date", style="cyan")
    table.add_column("Column")
    table.add_column("Price", justify="right")
    table.add_column("Underline")

    for p in pivots:
        ul_style = "bold red" if p.underline == "red" else "bold white"
        table.add_row(
            p.date,
            p.source_col.short,
            f"${p.price:.2f}",
            Text(p.underline, style=ul_style),
        )

    console.print(table)


def _render_signal_table(signals: Sequence[Signal], console: Console) -> None:
    table = Table(title="Trading Signals", box=box.ROUNDED)
    table.add_column("Date", style="cyan")
    table.add_column("Signal")
    table.add_column("Price", justify="right")
    table.add_column("Rule")
    table.add_column("Detail")

    for s in signals:
        style, label = SIGNAL_STYLES[s.signal_type]
        table.add_row(
            s.date,
            Text(label, style=style),
            f"${s.price:.2f}",
            s.rule,
            s.detail,
        )

    console.print(table)


# ── Group Sheet — the Livermore Map ──────────────────────────────────


def render_group_sheet(
    state: GroupState,
    console: Console | None = None,
) -> None:
    con = console or Console()
    a, b = group_leaders(state)
    trend = group_trend(state)
    t_style, t_label = TREND_STYLES[trend]

    con.print()
    con.print(
        f"  [bold]{state.config.name}[/]  Key Price: [{t_style}]{t_label}[/]",
        highlight=False,
    )
    con.print()

    _render_livermore_map(a, b, state.key_price, con)

    all_signals = [*a.engine.signals, *b.engine.signals]
    if state.key_price is not None:
        all_signals.extend(state.key_price.engine.signals)
    if all_signals:
        _render_signal_table(tuple(all_signals), con)

    tracked = group_tracked(state)
    for stock in tracked:
        con.print()
        title = f"{stock.ticker} (tracked) — swing={stock.config.swing:.1f}"
        _render_stock_mini(stock, title, con)


def _render_livermore_map(
    a: StockState,
    b: StockState,
    kp: StockState | None,
    console: Console,
) -> None:
    title = f"{a.ticker} + {b.ticker} — Livermore Map (18 columns)"
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=True)
    table.add_column("Date", style="cyan", width=12)

    for col in COL_ORDER:
        table.add_column(f"{a.ticker}\n{col.short}", justify="right", width=9)
    table.add_column("|", width=1)
    for col in COL_ORDER:
        table.add_column(f"{b.ticker}\n{col.short}", justify="right", width=9)
    table.add_column("|", width=1)
    for col in COL_ORDER:
        table.add_column(f"KEY\n{col.short}", justify="right", width=9)

    a_by_date = {e.date: e for e in a.engine.entries}
    b_by_date = {e.date: e for e in b.engine.entries}
    kp_by_date = {e.date: e for e in kp.engine.entries} if kp else {}
    all_dates = sorted(a_by_date.keys() | b_by_date.keys() | kp_by_date.keys())

    a_pivots = a.engine.pivots
    b_pivots = b.engine.pivots
    kp_pivots = kp.engine.pivots if kp else ()

    for date in all_dates:
        row: list[Text | str] = [date]

        ea = a_by_date.get(date)
        for col in COL_ORDER:
            if ea is not None and col is ea.col:
                row.append(format_price(ea.price, col, a_pivots))
            else:
                row.append("")

        row.append("")

        eb = b_by_date.get(date)
        for col in COL_ORDER:
            if eb is not None and col is eb.col:
                row.append(format_price(eb.price, col, b_pivots))
            else:
                row.append("")

        row.append("")

        ek = kp_by_date.get(date)
        for col in COL_ORDER:
            if ek is not None and col is ek.col:
                row.append(format_price(ek.price, col, kp_pivots))
            else:
                row.append("")

        table.add_row(*row)

    console.print(table)


# ── Dashboard Rendering ─────────────────────────────────────────────


def render_dashboard(
    state: MarketState,
    console: Console | None = None,
) -> None:
    con = console or Console()
    mkt = market_trend(state)
    mkt_style, mkt_label = TREND_STYLES[mkt]
    con.print()
    con.print(f"  Market Trend: [{mkt_style}]{mkt_label}[/]", highlight=False)
    con.print()

    _render_groups_table(state, con)

    for g in state.groups:
        _render_group_detail(g, con)


def _render_groups_table(state: MarketState, console: Console) -> None:
    table = Table(title="Livermore Market Key — Dashboard", box=box.SIMPLE_HEAVY)
    table.add_column("Group", style="bold")
    table.add_column("Leader A")
    table.add_column("A State", justify="center")
    table.add_column("Leader B")
    table.add_column("B State", justify="center")
    table.add_column("Key Price", justify="center")
    table.add_column("Trend", justify="center")
    table.add_column("Tracked", style="dim")

    for g in state.groups:
        a, b = group_leaders(g)
        tracked = group_tracked(g)
        trend = group_trend(g)
        t_style, t_label = TREND_STYLES[trend]
        kp_col = _col_text(g.key_price.engine.current) if g.key_price else Text("—", style="dim")

        table.add_row(
            g.config.name,
            a.ticker,
            _col_text(a.engine.current),
            b.ticker,
            _col_text(b.engine.current),
            kp_col,
            Text(t_label, style=t_style),
            ", ".join(s.ticker for s in tracked) or "—",
        )

    console.print(table)


def _render_group_detail(state: GroupState, console: Console) -> None:
    console.print()
    console.rule(f"[bold]{state.config.name}[/]")

    for stock in state.stocks:
        role = "leader" if stock.is_leader else "tracked"
        title = f"{stock.ticker} ({role}) — swing={stock.config.swing:.1f}"
        _render_stock_mini(stock, title, console)


def _render_stock_mini(stock: StockState, title: str, console: Console) -> None:
    table = Table(title=title, box=box.SIMPLE, show_lines=False, pad_edge=False)
    table.add_column("Date", style="cyan", width=12)
    for col in COL_ORDER:
        table.add_column(col.short, justify="right", width=10)

    for entry in stock.engine.entries:
        row: list[Text | str] = [entry.date]
        for col in COL_ORDER:
            if col is entry.col:
                row.append(format_price(entry.price, col, stock.engine.pivots))
            else:
                row.append("")
        table.add_row(*row)

    console.print(table)

    for s in stock.engine.signals:
        style, label = SIGNAL_STYLES[s.signal_type]
        console.print(f"    [{style}]{label}[/] ${s.price:.2f} Rule {s.rule} — {s.detail}")


def _col_text(col: Col | None) -> Text:
    if col is None:
        return Text("—", style="dim")
    style = INK_STYLES.get(col.ink, "dim")
    return Text(col.short, style=style)

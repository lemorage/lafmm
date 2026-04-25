from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from lafmm.group import group_leaders, group_tracked, group_trend, market_trend
from lafmm.models import (
    COL_ORDER,
    Col,
    Entry,
    GroupState,
    GroupTrend,
    MarketState,
    PivotalPoint,
    Signal,
    SignalType,
    StockState,
)
from lafmm.tui import INK_STYLES, format_price

DANGER_COLOR = "#ffaa00"

TREND_COLORS: dict[GroupTrend, str] = {
    "bullish": "green",
    "bearish": "red",
    "neutral": "yellow",
}


def _signal_text(signal_type: SignalType) -> Text:
    match signal_type:
        case SignalType.BUY:
            return Text("BUY", style="bold green")
        case SignalType.SELL:
            return Text("SELL", style="bold red")
        case SignalType.DANGER_UP_OVER:
            txt = Text("DANGER ", style=f"bold {DANGER_COLOR}")
            txt.append("▼", style="bold red")
            return txt
        case SignalType.DANGER_DOWN_OVER:
            txt = Text("DANGER ", style=f"bold {DANGER_COLOR}")
            txt.append("▲", style="bold green")
            return txt
        case SignalType.WATCH:
            return Text("WATCH", style="bold cyan")


CSS = """
Screen {
    background: $surface;
}

#market-header, #group-header, #stock-header {
    dock: top;
    height: 3;
    background: $primary-background;
    padding: 0 2;
    content-align: center middle;
}

#market-header.bullish, #group-header.bullish { color: $success; }
#market-header.bearish, #group-header.bearish { color: $error; }
#market-header.neutral, #group-header.neutral { color: $warning; }

#groups-table, #map-table {
    height: 1fr;
}

#tracked-table {
    height: auto;
    max-height: 30%;
    margin: 0;
}

#stock-table {
    height: 1fr;
}

.section-label {
    padding: 0 1;
    text-style: bold;
    color: $text;
    margin: 1 0 0 0;
}

.signal-line {
    padding: 0 2;
    margin: 0;
}
"""


# ── Helpers ──────────────────────────────────────────────────────────


def _entry_cells(
    entry: Entry | None,
    pivots: tuple[PivotalPoint, ...],
) -> list[Text | str]:
    return [
        format_price(entry.price, col, pivots) if entry is not None and col is entry.col else ""
        for col in COL_ORDER
    ]


_GOLD_START = (238, 207, 115)
_GOLD_END = (169, 132, 20)


def _gold_gradient(text: str, offset: int, total: int) -> Text:
    result = Text()
    for i, ch in enumerate(text):
        t = (offset + i) / max(total - 1, 1)
        r = int(_GOLD_START[0] + (_GOLD_END[0] - _GOLD_START[0]) * t)
        g = int(_GOLD_START[1] + (_GOLD_END[1] - _GOLD_START[1]) * t)
        b = int(_GOLD_START[2] + (_GOLD_END[2] - _GOLD_START[2]) * t)
        result.append(ch, style=f"rgb({r},{g},{b})")
    return result


def _gold_row(cells: list[str]) -> list[Text]:
    total = sum(len(c) for c in cells)
    result: list[Text] = []
    offset = 0
    for cell in cells:
        result.append(_gold_gradient(cell, offset, total))
        offset += len(cell)
    return result


def _populate_signal_table(
    table: DataTable,
    signals: list[tuple[str, Signal]],
    dim_key: bool = True,
) -> None:
    table.add_columns("Date", "Ticker", "Signal", "Detail", "Rule")
    sorted_signals = sorted(signals, key=lambda s: s[1].date, reverse=True)
    for source, signal in sorted_signals:
        is_key = source == "KEY"
        if is_key and dim_key:
            gold_cells = [signal.date, source, signal.detail, signal.rule]
            gold = _gold_row(gold_cells)
            table.add_row(
                gold[0],
                gold[1],
                _signal_text(signal.signal_type),
                gold[2],
                gold[3],
                key=f"key-{source}-{signal.date}-{signal.rule}",
            )
        else:
            table.add_row(
                signal.date,
                source,
                _signal_text(signal.signal_type),
                signal.detail,
                signal.rule,
                key=f"sig-{source}-{signal.date}-{signal.rule}",
            )


def _col_styled(col: Col | None) -> Text:
    if col is None:
        return Text("—", style="dim")
    return Text(col.short, style=INK_STYLES.get(col.ink, "dim"))


def _kp_short(state: GroupState) -> str:
    if state.key_price and state.key_price.engine.current:
        return state.key_price.engine.current.short
    return "—"


# ── Dashboard Screen ────────────────────────────────────────────────


class DashboardScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_group", "Open Group", priority=True),
    ]

    def __init__(self, state: MarketState) -> None:
        self.state = state
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()

        trend = market_trend(self.state)
        header = Label(
            f"Market Trend: {trend.upper()}  ({len(self.state.groups)} groups)",
            id="market-header",
        )
        header.add_class(trend)
        yield header

        yield DataTable(id="groups-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#groups-table", DataTable)
        table.add_columns(
            "Group",
            "Leader A",
            "A State",
            "Leader B",
            "B State",
            "Key Price",
            "Trend",
            "Tracked",
        )

        for i, g in enumerate(self.state.groups):
            a, b = group_leaders(g)
            tracked = group_tracked(g)
            trend = group_trend(g)
            t_color = TREND_COLORS[trend]
            table.add_row(
                g.config.name,
                a.ticker,
                _col_styled(a.engine.current),
                b.ticker,
                _col_styled(b.engine.current),
                Text(_kp_short(g), style="bold"),
                Text(trend.upper(), style=f"bold {t_color}"),
                ", ".join(s.ticker for s in tracked) or "—",
                key=str(i),
            )

    def action_select_group(self) -> None:
        table = self.query_one("#groups-table", DataTable)
        row = table.cursor_coordinate.row
        if row < len(self.state.groups):
            self.app.push_screen(GroupScreen(self.state.groups[row]))


# ── Group Screen (18-column Livermore Map) ───────────────────────────


class GroupScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("enter", "select_tracked", "Open Stock", priority=True),
        Binding("k", "toggle_key", "Toggle KEY", priority=True),
    ]

    def __init__(self, state: GroupState) -> None:
        self.state = state
        self._tracked = group_tracked(state)
        self._key_visible = True
        self._all_signals: list[tuple[str, Signal]] = []
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()

        trend = group_trend(self.state)
        header = Label(
            f"{self.state.config.name}  —  Key Price: {trend.upper()}",
            id="group-header",
        )
        header.add_class(trend)
        yield header

        a, b = group_leaders(self.state)

        with VerticalScroll():
            yield Label(
                f" {a.ticker} + {b.ticker} — Livermore Map",
                classes="section-label",
            )
            yield DataTable(id="map-table", cursor_type="row", zebra_stripes=True, fixed_columns=1)

            yield Label(" Signals", classes="section-label")
            yield Vertical(id="signals-container")

            if self._tracked:
                yield Label(" Tracked Stocks", classes="section-label")
                yield DataTable(
                    id="tracked-table",
                    cursor_type="row",
                    zebra_stripes=True,
                )

        yield Footer()

    def on_mount(self) -> None:
        a, b = group_leaders(self.state)
        kp = self.state.key_price

        self._populate_map(a, b, kp)
        self._populate_signals(a, b, kp)

        if self._tracked:
            self._populate_tracked_list()

    def _populate_map(
        self,
        a: StockState,
        b: StockState,
        kp: StockState | None,
    ) -> None:
        table = self.query_one("#map-table", DataTable)

        table.add_column("Date", key="date")
        for col in COL_ORDER:
            table.add_column(f"{a.ticker} {col.short}", key=f"a_{col.name}")
        table.add_column("|", key="sep1")
        for col in COL_ORDER:
            table.add_column(f"{b.ticker} {col.short}", key=f"b_{col.name}")
        table.add_column("|", key="sep2")
        for col in COL_ORDER:
            table.add_column(f"KEY {col.short}", key=f"k_{col.name}")

        a_by_date = {e.date: e for e in a.engine.entries}
        b_by_date = {e.date: e for e in b.engine.entries}
        kp_dates = {e.date: e for e in kp.engine.entries} if kp else {}
        all_dates = sorted(
            a_by_date.keys() | b_by_date.keys() | kp_dates.keys(),
        )
        kp_pivots = kp.engine.pivots if kp else ()

        for date in all_dates:
            row: list[Text | str] = [date]
            row.extend(_entry_cells(a_by_date.get(date), a.engine.pivots))
            row.append("")
            row.extend(_entry_cells(b_by_date.get(date), b.engine.pivots))
            row.append("")
            row.extend(_entry_cells(kp_dates.get(date), kp_pivots))
            table.add_row(*row)

    def _populate_signals(
        self,
        a: StockState,
        b: StockState,
        kp: StockState | None,
    ) -> None:
        container = self.query_one("#signals-container")
        self._all_signals = [
            *((a.ticker, s) for s in a.engine.signals),
            *((b.ticker, s) for s in b.engine.signals),
        ]
        if kp:
            self._all_signals.extend(("KEY", s) for s in kp.engine.signals)

        if not self._all_signals:
            container.mount(Label("  No signals yet.", classes="signal-line"))
            return

        table = DataTable(id="signal-table", cursor_type="none", zebra_stripes=True)
        container.mount(table)
        _populate_signal_table(table, self._all_signals)

    def _rebuild_signal_table(self) -> None:
        try:
            table = self.query_one("#signal-table", DataTable)
        except NoMatches:
            return
        table.clear(columns=True)
        if self._key_visible:
            _populate_signal_table(table, self._all_signals)
        else:
            stock_only = [(s, sig) for s, sig in self._all_signals if s != "KEY"]
            _populate_signal_table(table, stock_only)

    def action_toggle_key(self) -> None:
        self._key_visible = not self._key_visible
        self._rebuild_signal_table()

    def _populate_tracked_list(self) -> None:
        table = self.query_one("#tracked-table", DataTable)
        table.add_columns("Ticker", "State", "Entries", "Pivots", "Signals", "Swing")

        for i, stock in enumerate(self._tracked):
            sig_count = len(stock.engine.signals)
            table.add_row(
                stock.ticker,
                _col_styled(stock.engine.current),
                str(len(stock.engine.entries)),
                str(len(stock.engine.pivots)),
                Text(str(sig_count), style="bold green" if sig_count == 0 else "bold yellow"),
                f"{stock.config.swing:.1f}",
                key=str(i),
            )

    def action_select_tracked(self) -> None:
        if not self._tracked:
            return
        try:
            table = self.query_one("#tracked-table", DataTable)
        except NoMatches:
            return
        if not table.has_focus:
            return
        row = table.cursor_coordinate.row
        if row < len(self._tracked):
            self.app.push_screen(StockScreen(self._tracked[row]))

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Stock Screen (single tracked stock detail) ──────────────────────


class StockScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "go_back", "Back", priority=True),
    ]

    def __init__(self, stock: StockState) -> None:
        self.stock = stock
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()

        yield Label(
            f"{self.stock.ticker}  —  swing={self.stock.config.swing:.1f}",
            id="stock-header",
        )

        with VerticalScroll():
            yield DataTable(id="stock-table", cursor_type="row", zebra_stripes=True)

            if self.stock.engine.signals:
                yield Label(" Signals", classes="section-label")
                yield Vertical(id="stock-signals")

            if self.stock.engine.pivots:
                yield Label(" Pivotal Points", classes="section-label")
                yield DataTable(id="pivot-table", cursor_type="none", zebra_stripes=True)

        yield Footer()

    def on_mount(self) -> None:
        self._populate_table()
        if self.stock.engine.signals:
            self._populate_signals()
        if self.stock.engine.pivots:
            self._populate_pivots()

    def _populate_table(self) -> None:
        table = self.query_one("#stock-table", DataTable)
        table.add_column("Date", key="date")
        for col in COL_ORDER:
            table.add_column(col.short, key=col.name)

        for entry in self.stock.engine.entries:
            row: list[Text | str] = [entry.date]
            row.extend(_entry_cells(entry, self.stock.engine.pivots))
            table.add_row(*row)

    def _populate_signals(self) -> None:
        container = self.query_one("#stock-signals")
        signals = [(self.stock.ticker, s) for s in self.stock.engine.signals]
        table = DataTable(cursor_type="none", zebra_stripes=True)
        container.mount(table)
        _populate_signal_table(table, signals)

    def _populate_pivots(self) -> None:
        table = self.query_one("#pivot-table", DataTable)
        table.add_columns("Date", "Column", "Price", "Underline")

        for p in self.stock.engine.pivots:
            ul_style = "bold red" if p.underline == "red" else "bold white"
            table.add_row(
                p.date,
                p.source_col.short,
                f"${p.price:.2f}",
                Text(p.underline, style=ul_style),
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Help Screen ────────────────────────────────────────────────────


HELP_TEXT = (
    "[bold]LAFMM — Quick Reference[/]\n"
    "\n"
    "┌──────────┬──────────────────────────────┬─────────┐\n"
    "│ [bold]Signal[/]   │ [bold]Meaning[/]                      │ [bold]Rules[/]   │\n"
    "├──────────┼──────────────────────────────┼─────────┤\n"
    "│ [bold cyan]WATCH[/]    │ Approaching pivot            │ 9(a-c)  │\n"
    "│ [bold green]BUY[/]      │ Confirmed buy                │ 10(a,d) │\n"
    "│ [bold red]SELL[/]     │ Confirmed sell               │ 10(b,c) │\n"
    f"│ [bold {DANGER_COLOR}]DANGER[/] [bold red]▼[/]"
    " │ Uptrend may be ending        │ 10(e)   │\n"
    f"│ [bold {DANGER_COLOR}]DANGER[/] [bold green]▲[/]"
    " │ Downtrend may be ending      │ 10(f)   │\n"
    "└──────────┴──────────────────────────────┴─────────┘\n"
    "\n"
    "┌──────────┬─────────┬────────────────────────────────────────┐\n"
    "│ [bold]Column[/]   │ [bold]Ink[/]     │ [bold]State[/]                                  │\n"
    "├──────────┼─────────┼────────────────────────────────────────┤\n"
    "│ [dim]SecRally[/] │ [dim]pencil[/]  │ [dim]Indecisive rally (below last NR)[/]       │\n"
    "│ [dim]NatRally[/] │ [dim]pencil[/]  │ [dim]Rally from decline[/]                     │\n"
    "│ [bold]UPTREND[/]  │ [bold]black[/]   │ [bold]Confirmed uptrend[/]                      │\n"
    "│ [bold red]DNTREND[/]  │ [bold red]red[/]     │ [bold red]Confirmed downtrend[/]"
    "                    │\n"
    "│ [dim]NatReac[/]  │ [dim]pencil[/]  │ [dim]Reaction from rally[/]                    │\n"
    "│ [dim]SecReac[/]  │ [dim]pencil[/]  │ [dim]Indecisive reaction (above last NREAC)[/] │\n"
    "└──────────┴─────────┴────────────────────────────────────────┘\n"
    "\n"
    "┌───────────────────┬────────────────────────────────────────┐\n"
    "│ [bold]Pivot underline[/]   │ [bold]Meaning[/]                                │\n"
    "├───────────────────┼────────────────────────────────────────┤\n"
    "│ Black             │ Departure upward — support             │\n"
    "│ Red               │ Departure downward — resistance        │\n"
    "└───────────────────┴────────────────────────────────────────┘\n"
    "\n"
    "┌───────┬────────────────────────┐\n"
    "│ [bold]Key[/]   │ [bold]Action[/]                 │\n"
    "├───────┼────────────────────────┤\n"
    "│ ?     │ This help              │\n"
    "│ k     │ Toggle KEY signals     │\n"
    "│ Enter │ Open selected          │\n"
    "│ Esc   │ Back / close           │\n"
    "│ q     │ Quit                   │\n"
    "└───────┴────────────────────────┘"
)


class HelpScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "go_back", "Close", priority=True),
        Binding("question_mark", "go_back", "Close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static(HELP_TEXT)
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Main App ─────────────────────────────────────────────────────────


class LafmmApp(App):
    CSS = CSS
    TITLE = "LAFMM — Livermore's Anticipating Future Movements Map"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help"),
    ]

    def __init__(self, state: MarketState | GroupState) -> None:
        self.state = state
        super().__init__()

    def on_mount(self) -> None:
        match self.state:
            case MarketState():
                self.push_screen(DashboardScreen(self.state))
            case GroupState():
                self.push_screen(GroupScreen(self.state))

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

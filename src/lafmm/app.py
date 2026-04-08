from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

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

TREND_COLORS: dict[GroupTrend, str] = {
    "bullish": "green",
    "bearish": "red",
    "neutral": "yellow",
}

SIGNAL_ICONS: dict[SignalType, tuple[str, str]] = {
    SignalType.BUY: ("BUY", "green"),
    SignalType.SELL: ("SELL", "red"),
    SignalType.DANGER_UP_OVER: ("DANGER", "yellow"),
    SignalType.DANGER_DOWN_OVER: ("DANGER", "yellow"),
}

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

.signal-line.buy { color: $success; }
.signal-line.sell { color: $error; }
.signal-line.danger { color: $warning; }
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
    ]

    def __init__(self, state: GroupState) -> None:
        self.state = state
        self._tracked = group_tracked(state)
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
            yield DataTable(id="map-table", cursor_type="row", zebra_stripes=True)

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
        all_signals: list[tuple[str, Signal]] = [
            *((a.ticker, s) for s in a.engine.signals),
            *((b.ticker, s) for s in b.engine.signals),
        ]
        if kp:
            all_signals.extend(("KEY", s) for s in kp.engine.signals)

        if not all_signals:
            container.mount(Label("  No signals yet.", classes="signal-line"))
            return

        for source, signal in all_signals:
            icon, color = SIGNAL_ICONS[signal.signal_type]
            css_class = "buy" if color == "green" else ("sell" if color == "red" else "danger")
            container.mount(
                Label(
                    f"  {icon} {source} ${signal.price:.2f} Rule {signal.rule} — {signal.detail}",
                    classes=f"signal-line {css_class}",
                )
            )

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
        for signal in self.stock.engine.signals:
            icon, color = SIGNAL_ICONS[signal.signal_type]
            css_class = "buy" if color == "green" else ("sell" if color == "red" else "danger")
            container.mount(
                Label(
                    f"  {icon} ${signal.price:.2f} Rule {signal.rule} — {signal.detail}",
                    classes=f"signal-line {css_class}",
                )
            )

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


# ── Main App ─────────────────────────────────────────────────────────


class LafmmApp(App):
    CSS = CSS
    TITLE = "LAFMM — Livermore's Anticipating Future Movements Map"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
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

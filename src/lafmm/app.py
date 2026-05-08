from typing import ClassVar, Final

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from lafmm.colors import (
    BG,
    BG_CURSOR,
    BG_DEEP,
    BG_ELEVATED,
    BG_HOVER,
    BG_SUBTLE,
    DANGER,
    FG,
    FG_ACCENT,
    FG_DIM,
    FG_FAINT,
    FG_MUTED,
    KEY_GRAD_END,
    KEY_GRAD_START,
    NEGATIVE,
    NEUTRAL,
    POSITIVE,
    WATCH,
)
from lafmm.group import group_leaders, group_tracked, group_trend, market_trend
from lafmm.models import (
    COL_ORDER,
    Col,
    EngineState,
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
    "bullish": POSITIVE,
    "bearish": NEGATIVE,
    "neutral": NEUTRAL,
}

DEFAULT_ZOOM_DEPTH: Final[int] = 5


def trend_boundary(
    pivots: tuple[PivotalPoint, ...],
    depth: int,
) -> str | None:
    if depth <= 0:
        return None
    confirmed = [p for p in pivots if p.source_col.is_confirmed_trend]
    if not confirmed or depth > len(confirmed):
        return None
    return confirmed[-depth].date


def _filter_engine(
    engine: EngineState,
    start: str | None,
) -> tuple[tuple[Entry, ...], tuple[PivotalPoint, ...], tuple[Signal, ...]]:
    if start is None:
        return engine.entries, engine.pivots, engine.signals
    return (
        tuple(e for e in engine.entries if e.date >= start),
        tuple(p for p in engine.pivots if p.date >= start),
        tuple(s for s in engine.signals if s.date >= start),
    )


def _init_zoom(pivots: tuple[PivotalPoint, ...]) -> tuple[int, int]:
    confirmed = [p for p in pivots if p.source_col.is_confirmed_trend]
    total = len(confirmed)
    depth = min(DEFAULT_ZOOM_DEPTH, total) if confirmed else 0
    return total, depth


def _signal_text(signal_type: SignalType) -> Text:
    match signal_type:
        case SignalType.BUY:
            return Text("BUY", style=f"bold {POSITIVE}")
        case SignalType.SELL:
            return Text("SELL", style=f"bold {NEGATIVE}")
        case SignalType.DANGER_UP_OVER:
            txt = Text("DANGER ", style=f"bold {DANGER}")
            txt.append("▼", style=f"bold {NEGATIVE}")
            return txt
        case SignalType.DANGER_DOWN_OVER:
            txt = Text("DANGER ", style=f"bold {DANGER}")
            txt.append("▲", style=f"bold {POSITIVE}")
            return txt
        case SignalType.WATCH:
            return Text("WATCH", style=f"bold {WATCH}")


CSS = f"""
Screen {{
    background: {BG};
}}

Header {{
    background: {BG_DEEP};
    color: {FG_MUTED};
    dock: top;
    height: 1;
}}

Footer {{
    background: {BG_DEEP};
    color: {FG_MUTED};
}}

FooterKey .footer-key--key {{
    background: {BG_ELEVATED};
    color: {FG_ACCENT};
}}

FooterKey .footer-key--description {{
    color: {FG_MUTED};
}}

#market-header, #group-header, #stock-header {{
    dock: top;
    height: 2;
    background: {BG_ELEVATED};
    padding: 0 2;
    content-align: left middle;
    color: {FG_DIM};
}}

#market-header.bullish, #group-header.bullish {{ color: {POSITIVE}; }}
#market-header.bearish, #group-header.bearish {{ color: {NEGATIVE}; }}
#market-header.neutral, #group-header.neutral {{ color: {NEUTRAL}; }}

DataTable {{
    background: {BG};
}}

DataTable > .datatable--header {{
    background: {BG};
    color: {FG_MUTED};
    text-style: none;
}}

DataTable > .datatable--cursor {{
    background: {BG_CURSOR};
    color: {FG};
}}

DataTable > .datatable--hover {{
    background: {BG_HOVER};
}}

DataTable > .datatable--even-row {{
    background: {BG};
}}

DataTable > .datatable--odd-row {{
    background: {BG_SUBTLE};
}}

#groups-table {{
    height: 1fr;
}}

#map-table {{
    height: auto;
}}

#tracked-table {{
    height: auto;
    max-height: 20;
    margin: 0;
}}

#stock-table {{
    height: auto;
}}

.section-label {{
    padding: 0 1;
    color: {FG_MUTED};
    margin: 1 0 0 0;
}}

VerticalScroll {{
    scrollbar-color: {FG_FAINT};
    scrollbar-color-hover: {FG_MUTED};
    scrollbar-color-active: {FG_ACCENT};
    scrollbar-background: {BG};
    scrollbar-background-hover: {BG};
    scrollbar-background-active: {BG};
}}

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


_KEY_START = KEY_GRAD_START
_KEY_END = KEY_GRAD_END


def _key_gradient(text: str, offset: int, total: int) -> Text:
    result = Text()
    for i, ch in enumerate(text):
        t = (offset + i) / max(total - 1, 1)
        r = int(_KEY_START[0] + (_KEY_END[0] - _KEY_START[0]) * t)
        g = int(_KEY_START[1] + (_KEY_END[1] - _KEY_START[1]) * t)
        b = int(_KEY_START[2] + (_KEY_END[2] - _KEY_START[2]) * t)
        result.append(ch, style=f"rgb({r},{g},{b})")
    return result


def _key_row(cells: list[str]) -> list[Text]:
    total = sum(len(c) for c in cells)
    result: list[Text] = []
    offset = 0
    for cell in cells:
        result.append(_key_gradient(cell, offset, total))
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
            gold = _key_row(gold_cells)
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


def _trend_marker(trend: GroupTrend) -> Text:
    if trend == "bullish":
        return Text("●", style=POSITIVE)
    if trend == "bearish":
        return Text("●", style=NEGATIVE)
    return Text("○", style="dim")


def _col_styled(col: Col | None) -> Text:
    if col is None:
        return Text("—", style="dim")
    return Text(col.short, style=INK_STYLES.get(col.ink, "dim"))


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
            "",
            "Group",
            "Leader A",
            "A State",
            "Leader B",
            "B State",
            "Key Price",
            "Trend",
            "Tracked",
        )

        rank = {"bullish": 0, "neutral": 1, "bearish": 2}
        self._sorted = sorted(
            self.state.groups,
            key=lambda g: (rank[group_trend(g)], g.config.name),
        )

        for i, g in enumerate(self._sorted):
            a, b = group_leaders(g)
            tracked = group_tracked(g)
            trend = group_trend(g)
            t_color = TREND_COLORS[trend]
            kp_col = g.key_price.engine.current if g.key_price else None
            table.add_row(
                _trend_marker(trend),
                g.config.name,
                a.ticker,
                _col_styled(a.engine.current),
                b.ticker,
                _col_styled(b.engine.current),
                _col_styled(kp_col),
                Text(trend.upper(), style=f"bold {t_color}"),
                ", ".join(s.ticker for s in tracked) or "—",
                key=str(i),
            )

    def action_select_group(self) -> None:
        table = self.query_one("#groups-table", DataTable)
        row = table.cursor_coordinate.row
        if row < len(self._sorted):
            self.app.push_screen(GroupScreen(self._sorted[row]))


# ── Group Screen (18-column Livermore Map) ───────────────────────────


class GroupScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("enter", "select_tracked", "Open Stock", priority=True),
        Binding("k", "toggle_key", "Toggle KEY", show=False, priority=True),
        Binding("-", "zoom_out", "Zoom out", show=False, priority=True),
        Binding("+,=", "zoom_in", "Zoom in", show=False, priority=True),
    ]

    def __init__(self, state: GroupState) -> None:
        self.state = state
        self._tracked = group_tracked(state)
        self._key_visible = True
        self._all_signals: list[tuple[str, Signal]] = []
        pivots = state.key_price.engine.pivots if state.key_price else ()
        self._total_boundaries, self._zoom_depth = _init_zoom(pivots)
        super().__init__()

    def _header_text(self) -> str:
        trend = group_trend(self.state)
        return f"{self.state.config.name}  —  {trend.upper()}"

    def compose(self) -> ComposeResult:
        yield Header()

        header = Label(self._header_text(), id="group-header")
        header.add_class(group_trend(self.state))
        yield header

        with VerticalScroll():
            yield DataTable(id="map-table", cursor_type="row", zebra_stripes=True, fixed_columns=1)

            yield Label(" Signals", classes="section-label")
            yield DataTable(id="signal-table", cursor_type="none", zebra_stripes=True)

            if self._tracked:
                yield Label(" Tracked", classes="section-label")
                yield DataTable(
                    id="tracked-table",
                    cursor_type="row",
                    zebra_stripes=True,
                )

        yield Footer()

    def on_mount(self) -> None:
        self._rebuild()
        if self._tracked:
            self._populate_tracked_list()

    def _rebuild(self) -> None:
        kp = self.state.key_price
        pivots = kp.engine.pivots if kp else ()
        start = trend_boundary(pivots, self._zoom_depth)

        a, b = group_leaders(self.state)
        self._populate_map(a, b, kp, start)
        self._populate_signals(a, b, kp, start)

    def _map_columns(self, table: DataTable, a: StockState, b: StockState) -> None:
        table.add_column("Date", key="date")
        for col in COL_ORDER:
            table.add_column(f"{a.ticker} {col.short}", key=f"a_{col.name}")
        table.add_column("|", key="sep1")
        for col in COL_ORDER:
            table.add_column(f"{b.ticker} {col.short}", key=f"b_{col.name}")
        table.add_column("|", key="sep2")
        for col in COL_ORDER:
            table.add_column(f"KEY {col.short}", key=f"k_{col.name}")

    def _populate_map(
        self,
        a: StockState,
        b: StockState,
        kp: StockState | None,
        start: str | None,
    ) -> None:
        table = self.query_one("#map-table", DataTable)
        table.clear(columns=True)
        self._map_columns(table, a, b)

        a_entries, a_pivots, _ = _filter_engine(a.engine, start)
        b_entries, b_pivots, _ = _filter_engine(b.engine, start)
        kp_entries, kp_pivots, _ = _filter_engine(kp.engine, start) if kp else ((), (), ())

        a_by_date = {e.date: e for e in a_entries}
        b_by_date = {e.date: e for e in b_entries}
        kp_by_date = {e.date: e for e in kp_entries}

        for date in sorted(a_by_date.keys() | b_by_date.keys() | kp_by_date.keys()):
            row: list[Text | str] = [date]
            row.extend(_entry_cells(a_by_date.get(date), a_pivots))
            row.append("")
            row.extend(_entry_cells(b_by_date.get(date), b_pivots))
            row.append("")
            row.extend(_entry_cells(kp_by_date.get(date), kp_pivots))
            table.add_row(*row)

    def _populate_signals(
        self,
        a: StockState,
        b: StockState,
        kp: StockState | None,
        start: str | None,
    ) -> None:
        _, _, a_sigs = _filter_engine(a.engine, start)
        _, _, b_sigs = _filter_engine(b.engine, start)

        self._all_signals = [
            *((a.ticker, s) for s in a_sigs),
            *((b.ticker, s) for s in b_sigs),
        ]
        if kp:
            _, _, kp_sigs = _filter_engine(kp.engine, start)
            self._all_signals.extend(("KEY", s) for s in kp_sigs)

        self._render_signal_table()

    def _render_signal_table(self) -> None:
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
        self._render_signal_table()

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
                Text(
                    str(sig_count),
                    style=f"bold {POSITIVE}" if sig_count == 0 else f"bold {NEUTRAL}",
                ),
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

    def action_zoom_out(self) -> None:
        if self._zoom_depth > 0:
            self._zoom_depth -= 1
            self._rebuild()

    def action_zoom_in(self) -> None:
        if self._zoom_depth < self._total_boundaries:
            self._zoom_depth += 1
            self._rebuild()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Stock Screen (single tracked stock detail) ──────────────────────


class StockScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("-", "zoom_out", "Zoom out", show=False, priority=True),
        Binding("+,=", "zoom_in", "Zoom in", show=False, priority=True),
    ]

    def __init__(self, stock: StockState) -> None:
        self.stock = stock
        self._total_boundaries, self._zoom_depth = _init_zoom(stock.engine.pivots)
        super().__init__()

    def _header_text(self) -> str:
        return f"{self.stock.ticker}  —  swing {self.stock.config.swing:.1f}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._header_text(), id="stock-header")

        with VerticalScroll():
            yield DataTable(id="stock-table", cursor_type="row", zebra_stripes=True)

            if self.stock.engine.signals:
                yield Label(" Signals", classes="section-label")
                yield DataTable(id="stock-signal-table", cursor_type="none", zebra_stripes=True)

            if self.stock.engine.pivots:
                yield Label(" Pivotal Points", classes="section-label")
                yield DataTable(id="pivot-table", cursor_type="none", zebra_stripes=True)

        yield Footer()

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        start = trend_boundary(self.stock.engine.pivots, self._zoom_depth)
        entries, pivots, signals = _filter_engine(self.stock.engine, start)

        self._populate_table(entries, pivots)
        if self.stock.engine.signals:
            self._populate_signals(signals)
        if self.stock.engine.pivots:
            self._populate_pivots(pivots)

    def _populate_table(
        self,
        entries: tuple[Entry, ...],
        pivots: tuple[PivotalPoint, ...],
    ) -> None:
        table = self.query_one("#stock-table", DataTable)
        table.clear(columns=True)
        table.add_column("Date", key="date")
        for col in COL_ORDER:
            table.add_column(col.short, key=col.name)

        for entry in entries:
            row: list[Text | str] = [entry.date]
            row.extend(_entry_cells(entry, pivots))
            table.add_row(*row)

    def _populate_signals(self, signals: tuple[Signal, ...]) -> None:
        table = self.query_one("#stock-signal-table", DataTable)
        table.clear(columns=True)
        tagged = [(self.stock.ticker, s) for s in signals]
        _populate_signal_table(table, tagged)

    def _populate_pivots(self, pivots: tuple[PivotalPoint, ...]) -> None:
        table = self.query_one("#pivot-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Column", "Price", "Underline")

        for p in pivots:
            ul_style = NEGATIVE if p.underline == "red" else FG
            table.add_row(
                p.date,
                p.source_col.short,
                f"${p.price:.2f}",
                Text(p.underline, style=ul_style),
            )

    def action_zoom_out(self) -> None:
        if self._zoom_depth > 0:
            self._zoom_depth -= 1
            self._rebuild()

    def action_zoom_in(self) -> None:
        if self._zoom_depth < self._total_boundaries:
            self._zoom_depth += 1
            self._rebuild()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Help Screen ────────────────────────────────────────────────────


HELP_TEXT = (
    "[bold]LAFMM — Quick Reference[/]\n"
    "\n"
    "┌──────────┬──────────────────────────────┬─────────┐\n"
    "│ [bold]Signal[/]   │ [bold]Meaning[/]                      │ [bold]Rules[/]   │\n"
    "├──────────┼──────────────────────────────┼─────────┤\n"
    f"│ [bold {WATCH}]WATCH[/]    │ Approaching pivot            │ 9(a-c)  │\n"
    f"│ [bold {POSITIVE}]BUY[/]      │ Confirmed buy                │ 10(a,d) │\n"
    f"│ [bold {NEGATIVE}]SELL[/]     │ Confirmed sell               │ 10(b,c) │\n"
    f"│ [bold {DANGER}]DANGER[/] [bold {NEGATIVE}]▼[/]"
    " │ Uptrend may be ending        │ 10(e)   │\n"
    f"│ [bold {DANGER}]DANGER[/] [bold {POSITIVE}]▲[/]"
    " │ Downtrend may be ending      │ 10(f)   │\n"
    "└──────────┴──────────────────────────────┴─────────┘\n"
    "\n"
    "┌──────────┬─────────┬────────────────────────────────────────┐\n"
    "│ [bold]Column[/]   │ [bold]Ink[/]     │ [bold]State[/]                                  │\n"
    "├──────────┼─────────┼────────────────────────────────────────┤\n"
    "│ [dim]SecRally[/] │ [dim]pencil[/]  │ [dim]Indecisive rally (below last NR)[/]       │\n"
    "│ [dim]NatRally[/] │ [dim]pencil[/]  │ [dim]Rally from decline[/]                     │\n"
    f"│ [{POSITIVE}]UPTREND[/]  │ [bold]black[/]   │ [{POSITIVE}]Confirmed uptrend[/]"
    "                      │\n"
    f"│ [{NEGATIVE}]DNTREND[/]  │ [{NEGATIVE}]red[/]     │ [{NEGATIVE}]Confirmed downtrend[/]"
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
    "│ -     │ Zoom out (more hist.)  │\n"
    "│ +     │ Zoom in (less hist.)   │\n"
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

"""Beautiful terminal stats dashboard for LAFMM trading performance."""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lafmm.chart import sparkline, vertical_bars

MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def render_stats(data: dict, console: Console | None = None) -> None:
    con = console or Console()
    con.print()
    _header(data, con)
    con.print()
    con.print(_grid("Performance", _perf_pairs(data)))
    con.print()
    con.print(_grid("Risk", _risk_pairs(data)))
    for rob in data.get("robustness", []):
        if rob.get("round_trips", 0) > 0:
            reason = rob.get("reason", "")
            title = f"excl. {reason} → {rob['excluded']}" if reason else f"excl. {rob['excluded']}"
            con.print()
            con.print(_grid(f"Robustness ({title})", _robustness_pairs(rob)))
    if data.get("rolling"):
        con.print()
        _render_rolling(data, con)
    con.print()
    _monthly(data, con)
    con.print()
    _symbols(data, con)
    con.print()
    con.print(_grid("Capital", _capital_pairs(data)))
    con.print()
    con.print(_grid("Costs & Income", _costs_pairs(data)))
    con.print()
    _behavior(data, con)
    if data.get("genome"):
        con.print()
        _render_genome(data, con)
    if data.get("regime"):
        con.print()
        _render_regime(data, con)
    con.print()


# ── Grid panel helper ───────────────────────────────────────────────


def _grid(title: str, pairs: Sequence[tuple[str, str]]) -> Panel:
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    t.add_column(style="bold", ratio=3)
    t.add_column(justify="right", ratio=2)
    t.add_column(min_width=4)
    t.add_column(style="bold", ratio=3)
    t.add_column(justify="right", ratio=2)

    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        t.add_row(left[0], left[1], "", right[0], right[1])

    return Panel(t, title=f"[bold]{title}[/]", border_style="blue", padding=(1, 1))


# ── Header with hero metrics ────────────────────────────────────────


def _header(data: dict, con: Console) -> None:
    period = data.get("period", "all")
    note = f"  [dim]period: {period}[/]" if period != "all" else ""

    months = data.get("monthly_pnl", [])
    cumulative = list(itertools.accumulate(m["pnl"] for m in months))
    ret = data["trading_return_pct"]
    spark = sparkline(cumulative, "green" if ret >= 0 else "red") if cumulative else ""

    t = Table(box=None, show_header=False, expand=True, padding=(0, 2))
    t.add_column()
    t.add_column(justify="right", no_wrap=True)

    rc = "green" if ret >= 0 else "red"
    pnl = data["total_pnl"]
    pc = "green" if pnl >= 0 else "red"
    ps = "+" if pnl >= 0 else "-"

    t.add_row(
        _date_markup(data, note),
        Text.from_markup(
            f"Return [bold {rc}]{ret:+.1f}%[/]    P&L [bold {pc}]{ps}${abs(pnl):,.2f}[/]"
        ),
    )
    t.add_row(*_second_row(data, ret, spark))

    con.print(Panel(t, title="[bold]LAFMM Trading Stats[/]", border_style="blue"))


def _date_markup(data: dict, note: str) -> Text:
    return Text.from_markup(
        f"[bold]{data['first_date']} → {data['last_date']}[/]  ·  "
        f"{data['market_days']} mkt days, {data['active_days']} active{note}"
    )


def _second_row(data: dict, ret: float, spark: str) -> tuple[Text, Text]:
    spy = data.get("spy_return_pct")
    if spy is not None:
        diff = ret - spy
        dc = "green" if diff >= 0 else "red"
        return (
            Text.from_markup(f"Equity  {spark}"),
            Text.from_markup(f"[dim]SPY {spy:+.1f}%[/]    [{dc}]vs benchmark {diff:+.1f}%[/]"),
        )
    return (Text.from_markup(f"Equity  {spark}"), Text(""))


# ── Section data ────────────────────────────────────────────────────


def _perf_pairs(data: dict) -> list[tuple[str, str]]:
    d = data
    pf = d.get("profit_factor", 0.0)
    pf_c = _pf_color(pf)

    rt = d.get("round_trips", 0)
    op = d.get("open_positions", 0)
    rt_label = f"{rt} [dim](+{op} open)[/]" if op > 0 else str(rt)

    pairs: list[tuple[str, str]] = [
        ("Executions", str(d["total_trades"])),
        ("Round Trips", rt_label),
        ("Wins / Losses", f"{d['wins']} / {d['losses']}"),
        ("Buys / Sells", f"{d['buys']} / {d['sells']}"),
        ("Win Rate", _pct(d["win_rate"])),
    ]
    for order_type, count in d.get("order_types", {}).items():
        pairs.append((f"{order_type.title()} Orders", str(count)))
    pairs.extend(
        [
            ("Total P&L", _pnl(d["total_pnl"])),
            ("Avg Win", _pnl(d["avg_win"])),
            ("Avg Loss", _pnl(d["avg_loss"])),
            ("Largest Win", _pnl(d["largest_win"])),
            ("Largest Loss", _pnl(d["largest_loss"])),
            ("Expectancy", _pnl(d["expectancy"])),
            ("Profit Factor", f"[{pf_c}]{pf:.2f}[/]" if pf > 0 else "N/A"),
        ]
    )
    return pairs


def _risk_pairs(data: dict) -> list[tuple[str, str]]:
    d = data
    return [
        ("Max Drawdown", f"[red]-{d['max_drawdown_pct']:.1f}%[/]"),
        ("Drawdown Days", str(d["max_drawdown_days"])),
        ("Win Streak", f"[green]{d['longest_win_streak']}[/]"),
        ("Loss Streak", f"[red]{d['longest_loss_streak']}[/]"),
        ("Sharpe Ratio", f"{d['sharpe']:.2f}"),
    ]


def _robustness_pairs(rob: dict) -> list[tuple[str, str]]:
    pf = rob.get("profit_factor", 0.0)
    pf_c = _pf_color(pf)
    return [
        ("Round Trips", str(rob["round_trips"])),
        ("Wins / Losses", f"{rob['wins']} / {rob['losses']}"),
        ("Win Rate", _pct(rob["win_rate"])),
        ("Expectancy", _pnl(rob["expectancy"])),
        ("Profit Factor", f"[{pf_c}]{pf:.2f}[/]" if pf > 0 else "N/A"),
    ]


def _capital_pairs(data: dict) -> list[tuple[str, str]]:
    d = data
    pairs = [
        ("Start", f"${d['start_capital']:,.2f}"),
        ("End", f"${d['end_capital']:,.2f}"),
        ("Deposits", f"${d['total_deposits']:,.2f}"),
        ("Withdrawals", f"${d['total_withdrawals']:,.2f}"),
        ("Trading Return", _pct(d["trading_return_pct"])),
    ]
    spy = d.get("spy_return_pct")
    if spy is not None:
        pairs.append(("SPY Return", _pct(spy)))
    return pairs


def _costs_pairs(data: dict) -> list[tuple[str, str]]:
    d = data
    return [
        ("Trading Fees", f"[red]${d['total_fees']:,.2f}[/]"),
        ("Fees % of P&L", f"{d['fees_pct_of_pnl']:.1f}%"),
        ("Platform Fees", f"[red]${d.get('total_platform_fees', 0):,.2f}[/]"),
        ("Dividends", f"[green]+${d['total_dividends']:,.2f}[/]"),
        ("Tax Withheld", f"[red]${d['total_tax']:,.2f}[/]"),
        ("Net Interest", _pnl(d["total_interest"])),
    ]


# ── Rolling metrics ─────────────────────────────────────────────────


def _rolling_rows(data: dict) -> list[tuple[str, str, str, str]]:
    rolling = data["rolling"]
    win_rates = [p["win_rate"] for p in rolling]
    expectancies = [p["expectancy"] for p in rolling]
    profit_factors = [p["profit_factor"] for p in rolling]

    avg_win_rate = data.get("win_rate", 0.0)
    avg_expectancy = data.get("expectancy", 0.0)
    avg_profit_factor = data.get("profit_factor", 0.0)
    expectancy_color = "green" if expectancies[-1] >= 0 else "red"
    profit_factor_color = _pf_color(profit_factors[-1])

    return [
        (
            "Win Rate",
            sparkline(win_rates, "cyan"),
            f"[cyan]{win_rates[-1]:.0f}%[/]",
            f"avg {avg_win_rate:.0f}%",
        ),
        (
            "Expectancy",
            sparkline(expectancies, expectancy_color),
            f"[{expectancy_color}]${expectancies[-1]:,.0f}[/]",
            f"avg ${avg_expectancy:,.0f}",
        ),
        (
            "Profit Factor",
            sparkline(profit_factors, "magenta"),
            f"[{profit_factor_color}]{profit_factors[-1]:.2f}[/]",
            f"avg {avg_profit_factor:.2f}",
        ),
    ]


def _render_rolling(data: dict, con: Console) -> None:
    window = data["rolling"][0]["window"]
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    t.add_column(style="bold", no_wrap=True)
    t.add_column(ratio=1)
    t.add_column(justify="right", no_wrap=True)
    t.add_column(justify="right", no_wrap=True, style="dim")
    for row in _rolling_rows(data):
        t.add_row(*row)
    con.print(
        Panel(
            t,
            title=f"[bold]Rolling {window}-Trip Metrics[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


# ── Monthly P&L chart ───────────────────────────────────────────────


def _monthly(data: dict, con: Console) -> None:
    months = data.get("monthly_pnl", [])
    if not months:
        return
    labels = [MONTH_NAMES[int(m["month"].split("-")[1]) - 1] for m in months]
    values = [m["pnl"] for m in months]

    n = len(months)
    available = con.width - 16
    bw = max(2, min(10, (available - n) // n))
    chart = vertical_bars(labels, values, height=8, bar_width=bw)

    con.print(
        Panel(
            Text.from_markup(chart),
            title="[bold]Monthly P&L[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


WIN_RATE_GOOD = 60
WIN_RATE_NEUTRAL = 50


def _win_rate_color(rate: float) -> str:
    if rate >= WIN_RATE_GOOD:
        return "green"
    return "yellow" if rate >= WIN_RATE_NEUTRAL else "red"


# ── Top symbols ─────────────────────────────────────────────────────


def _symbols(data: dict, con: Console) -> None:
    symbols = data.get("top_symbols", [])
    if not symbols:
        return
    n_traded = data.get("symbols_traded", len(symbols))

    t = Table(box=None, show_header=True, expand=True, padding=(0, 1))
    t.add_column("Symbol", style="bold", no_wrap=True)
    t.add_column("P&L", justify="right", no_wrap=True)
    t.add_column("Trips", justify="right", no_wrap=True)
    t.add_column("W/L", justify="right", no_wrap=True)
    t.add_column("Win Rate", justify="right", no_wrap=True)

    for s in symbols:
        trip_count = s.get("round_trips", 0)
        win_count = s.get("wins", 0)
        loss_count = s.get("losses", 0)
        win_rate = s.get("win_rate", 0.0)
        win_rate_color = _win_rate_color(win_rate)
        t.add_row(
            s["symbol"],
            _pnl(s["pnl"]),
            str(trip_count) if trip_count else "—",
            f"{win_count}/{loss_count}" if trip_count else "—",
            f"[{win_rate_color}]{win_rate:.0f}%[/]" if trip_count else "—",
        )

    conc = data.get("concentration_pct", 0.0)
    footer = ""
    if conc > 0 and symbols:
        style = "red" if conc > 50 else ("yellow" if conc > 30 else "dim")
        footer = f"\n  [{style}]{conc:.0f}% concentration in {symbols[0]['symbol']}[/]"

    content = Group(t, Text.from_markup(footer)) if footer else t

    con.print(
        Panel(
            content,
            title=f"[bold]Top Symbols[/]  [dim]({n_traded} traded)[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


# ── Behavior ────────────────────────────────────────────────────────


def _behavior_row(
    t: Table,
    label: str,
    count: int,
    win_rate: float,
    indent: bool = False,
) -> None:
    prefix = "  " if indent else ""
    t.add_row(f"{prefix}{label}", str(count), _pct(win_rate))


def _behavior(data: dict, con: Console) -> None:
    d = data
    total = d.get("round_trips", 0)
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    t.add_column(style="bold", no_wrap=True, ratio=3)
    t.add_column(justify="right", ratio=1)
    t.add_column(justify="right", ratio=2)

    t.add_row("Total Positions", str(total), _pct(d.get("win_rate", 0.0)))
    t.add_row()

    pre = d.get("pre_system_trades", 0)
    if pre > 0:
        _behavior_row(t, "Pre-System", pre, d.get("pre_system_win_rate", 0.0))

    post = d.get("post_system_trades", 0)
    if post > 0:
        _behavior_row(t, "Post-System", post, d.get("post_system_win_rate", 0.0))
        signal_count = d.get("signal_trades", 0)
        discretionary_count = d.get("discretionary_trades", 0)
        if signal_count > 0:
            _behavior_row(t, "Signaled", signal_count, d.get("signal_win_rate", 0.0), indent=True)
        if discretionary_count > 0:
            discretionary_win_rate = d.get("discretionary_win_rate", 0.0)
            _behavior_row(
                t, "Discretionary", discretionary_count, discretionary_win_rate, indent=True
            )

    avg_hold = d.get("avg_hold_days", 0.0)
    longest = d.get("longest_hold_days", 0)
    if avg_hold > 0 or longest > 0:
        t.add_row()
        sym = d.get("longest_hold_symbol", "")
        t.add_row("Avg Hold", f"{avg_hold:.1f}d", "")
        t.add_row("Longest Hold", f"{longest}d {sym}" if sym else f"{longest}d", "")

    con.print(Panel(t, title="[bold]Behavior[/]", border_style="blue", padding=(1, 1)))


# ── Trade Genome ───────────────────────────────────────────────────

REGIME_LABELS: dict[str, str] = {
    "BULL": "Bull",
    "STRESS": "Stress",
    "COMPLACENT": "Complacent",
    "BEAR": "Bear",
    "CHOP": "Chop",
    "PANIC": "Panic",
    "?": "Unknown",
}

REGIME_COLORS: dict[str, str] = {
    "BULL": "green",
    "STRESS": "yellow",
    "COMPLACENT": "red",
    "BEAR": "red",
    "CHOP": "dim",
    "PANIC": "bold red",
    "?": "dim",
}

REGIME_ORDER: tuple[str, ...] = ("BULL", "STRESS", "CHOP", "COMPLACENT", "BEAR", "PANIC", "?")


def _render_regime(data: dict, con: Console) -> None:
    buckets = data.get("regime", [])
    if not buckets:
        return

    def _regime_rank(bucket: dict) -> int:
        regime = bucket["label"]
        return REGIME_ORDER.index(regime) if regime in REGIME_ORDER else 99

    ordered = sorted(buckets, key=_regime_rank)

    total = sum(b["trades"] for b in ordered)
    bar_width = max(40, con.width - 12)
    bar_parts: list[str] = []
    for bucket in ordered:
        width = max(1, round(bucket["trades"] / total * bar_width))
        color = REGIME_COLORS.get(bucket["label"], "dim")
        bar_parts.append(f"[{color}]{'█' * width}[/]")

    legend = Table(box=None, show_header=False, padding=(0, 1), pad_edge=False)
    legend.add_column(no_wrap=True, min_width=4)
    legend.add_column(style="bold", no_wrap=True, min_width=12)
    legend.add_column(justify="right", min_width=4)
    legend.add_column(justify="right", min_width=5)
    legend.add_column(justify="right", min_width=8)
    for bucket in ordered:
        regime = bucket["label"]
        color = REGIME_COLORS.get(regime, "dim")
        label = REGIME_LABELS.get(regime, regime)
        win_rate = bucket["win_rate"]
        legend.add_row(
            f"  [{color}]■[/]",
            label,
            str(bucket["trades"]),
            f"[{_win_rate_color(win_rate)}]{win_rate:.0f}%[/]",
            _pnl(bucket["pnl"]),
        )

    con.print(
        Panel(
            Group(
                Text.from_markup(f"  {''.join(bar_parts)}"),
                legend,
            ),
            title="[bold]Market Regime[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


GENOME_LABELS: dict[str, str] = {
    "W": "With-trend",
    "N": "Neutral",
    "A": "Against-trend",
    "F": "Flash",
    "S": "Swing",
    "P": "Position",
    "B": "Breakout",
    "K": "Pullback",
    "R": "Reversal",
    "C": "Confirmed",
    "U": "Unconfirmed",
}

GENOME_AXES: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("Trend", 0, ("W", "N", "A")),
    ("Setup", 2, ("B", "K", "R")),
    ("Cadence", 1, ("F", "S", "P")),
    ("Volume", 3, ("C", "U")),
)

GENOME_COLORS: tuple[str, ...] = ("cyan", "magenta", "yellow", "green", "blue")

EDGE_LEAK_COUNT = 3


@dataclass(frozen=True, slots=True)
class _AxisSegment:
    label: str
    trades: int
    wins: int
    pnl: float

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0.0


def _aggregate_axis(
    buckets: Sequence[dict],
    axis_idx: int,
    keys: Sequence[str],
) -> list[_AxisSegment]:
    segments: list[_AxisSegment] = []
    for code_letter in keys:
        label = GENOME_LABELS.get(code_letter, code_letter)
        trades = wins = 0
        pnl = 0.0
        for bucket in buckets:
            if bucket["label"] == "?":
                continue
            parts = bucket["label"].split("-")
            if len(parts) > axis_idx and parts[axis_idx] == code_letter:
                trades += bucket["trades"]
                wins += bucket["wins"]
                pnl += bucket["pnl"]
        if trades > 0:
            segments.append(_AxisSegment(label, trades, wins, round(pnl, 2)))
    return segments


def _render_proportion_bar(
    segments: Sequence[_AxisSegment],
    width: int,
) -> str:
    total = sum(segment.trades for segment in segments)
    if total == 0:
        return ""
    parts: list[str] = []
    for i, segment in enumerate(segments):
        segment_width = max(1, round(segment.trades / total * width))
        color = GENOME_COLORS[i % len(GENOME_COLORS)]
        parts.append(f"[{color}]{'█' * segment_width}[/]")
    return "".join(parts)


def _render_axis_legend(
    segments: Sequence[_AxisSegment],
) -> Table:
    legend = Table(box=None, show_header=False, padding=(0, 1), pad_edge=False)
    legend.add_column(no_wrap=True, min_width=4)
    legend.add_column(style="bold", no_wrap=True, min_width=12)
    legend.add_column(justify="right", min_width=4)
    legend.add_column(justify="right", min_width=5)
    legend.add_column(justify="right", min_width=8)
    for i, segment in enumerate(segments):
        color = GENOME_COLORS[i % len(GENOME_COLORS)]
        win_rate = segment.win_rate
        wr_color = _win_rate_color(win_rate)
        legend.add_row(
            f"  [{color}]■[/]",
            segment.label,
            str(segment.trades),
            f"[{wr_color}]{win_rate:.0f}%[/]",
            _pnl(segment.pnl),
        )
    return legend


def _render_genome_row(table: Table, bucket: dict) -> None:
    code = bucket["label"]
    win_rate = bucket["win_rate"]
    color = _win_rate_color(win_rate)
    parts = code.split("-")
    hint = " ".join(GENOME_LABELS.get(part) or part for part in parts)
    table.add_row(
        f"  {code}",
        str(bucket["trades"]),
        f"[{color}]{win_rate:.0f}%[/]",
        _pnl(bucket["pnl"]),
        hint,
    )


def _make_edge_leak_table() -> Table:
    table = Table(box=None, show_header=False, padding=(0, 1), pad_edge=False)
    table.add_column(style="bold", no_wrap=True, min_width=12)
    table.add_column(justify="right", min_width=4)
    table.add_column(justify="right", min_width=5)
    table.add_column(justify="right", min_width=8)
    table.add_column(style="dim", no_wrap=True)
    return table


def _render_edge_and_leak(buckets: Sequence[dict]) -> tuple[Table, Table]:
    classified = [b for b in buckets if b["label"] != "?"]
    winners = sorted([b for b in classified if b["pnl"] > 0], key=lambda b: -b["pnl"])
    losers = sorted([b for b in classified if b["pnl"] < 0], key=lambda b: b["pnl"])

    edge = _make_edge_leak_table()
    for bucket in winners[:EDGE_LEAK_COUNT]:
        _render_genome_row(edge, bucket)

    leak = _make_edge_leak_table()
    for bucket in losers[:EDGE_LEAK_COUNT]:
        _render_genome_row(leak, bucket)

    return edge, leak


def _build_axis_parts(
    buckets: Sequence[dict],
    bar_width: int,
) -> list[Text | Table]:
    parts: list[Text | Table] = []
    for axis_name, axis_idx, keys in GENOME_AXES:
        segments = _aggregate_axis(buckets, axis_idx, keys)
        if not segments:
            continue
        bar = _render_proportion_bar(segments, bar_width)
        parts.append(Text.from_markup(f"  [bold]{axis_name}[/]"))
        parts.append(Text.from_markup(f"  {bar}"))
        parts.append(_render_axis_legend(segments))
        parts.append(Text(""))
    return parts


def _render_genome(data: dict, con: Console) -> None:
    buckets = data.get("genome", [])
    if not buckets:
        return

    parts = _build_axis_parts(buckets, max(40, con.width - 12))
    edge, leak = _render_edge_and_leak(buckets)
    parts.append(Text.from_markup("  [bold green]Edge[/]"))
    parts.append(edge)
    parts.append(Text(""))
    parts.append(Text.from_markup("  [bold red]Leak[/]"))
    parts.append(leak)

    con.print(
        Panel(Group(*parts), title="[bold]Trade Genome[/]", border_style="blue", padding=(1, 2))
    )


# ── Formatting helpers ──────────────────────────────────────────────


def _pf_color(profit_factor: float) -> str:
    if profit_factor >= 1.5:
        return "green"
    return "yellow" if profit_factor >= 1.0 else "red"


def _pnl(v: float) -> str:
    if v > 0:
        return f"[green]+${v:,.2f}[/]"
    if v < 0:
        return f"[red]-${abs(v):,.2f}[/]"
    return "$0.00"


def _pct(v: float) -> str:
    if v > 0:
        return f"[green]+{v:.1f}%[/]"
    if v < 0:
        return f"[red]{v:.1f}%[/]"
    return "0.0%"


# ── Public API ──────────────────────────────────────────


def resolve_account(accounts_dir: Path, name: str | None) -> Path:
    if not accounts_dir.exists():
        click.echo("no accounts found — run lafmm first")
        sys.exit(1)
    if name:
        return accounts_dir / name
    accts = [d for d in accounts_dir.iterdir() if d.is_dir()]
    if not accts:
        click.echo("no accounts found")
        sys.exit(1)
    if len(accts) == 1:
        return accts[0]
    click.echo("multiple accounts — specify one:")
    for a in accts:
        click.echo(f"  lafmm stats {a.name}")
    sys.exit(1)


def _find_compute_script(lafmm_dir: Path) -> Path:
    script = lafmm_dir / ".claude" / "skills" / "stats" / "scripts" / "compute.py"
    if script.exists():
        return script
    repo = Path(__file__).resolve().parent.parent.parent
    return repo / "skills" / "stats" / "scripts" / "compute.py"


def run_compute(
    lafmm_dir: Path,
    account_dir: Path,
    period: str | None,
    benchmark: bool,
) -> dict:
    if not (account_dir / "journal").exists():
        click.echo(f"no journal in {account_dir.name}")
        sys.exit(1)

    cmd = [sys.executable, str(_find_compute_script(lafmm_dir)), str(account_dir)]
    if period:
        cmd.extend(["--period", period])
    if benchmark:
        spy_dir = lafmm_dir / "data" / "us-indices" / "SPY"
        if spy_dir.exists():
            cmd.extend(["--benchmark", str(spy_dir)])
    data_dir = lafmm_dir / "data"
    if data_dir.exists():
        cmd.extend(["--data-dir", str(data_dir)])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        click.echo(f"error: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout)

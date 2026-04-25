"""Beautiful terminal stats dashboard for LAFMM trading performance."""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lafmm.chart import horizontal_bars, sparkline, vertical_bars

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
    con.print(_grid("Behavior", _behavior_pairs(data)))
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


# ── Top symbols ─────────────────────────────────────────────────────


def _symbols(data: dict, con: Console) -> None:
    symbols = data.get("top_symbols", [])
    if not symbols:
        return
    labels = [s["symbol"] for s in symbols]
    values = [s["pnl"] for s in symbols]
    n_traded = data.get("symbols_traded", len(symbols))

    label_w = max(len(s) for s in labels)
    bar_w = max(20, con.width - label_w - 30)
    chart = horizontal_bars(labels, values, width=bar_w)

    content = chart
    conc = data.get("concentration_pct", 0.0)
    if conc > 0 and symbols:
        style = "red" if conc > 50 else ("yellow" if conc > 30 else "dim")
        content += f"\n\n  [{style}]{conc:.0f}% concentration in {symbols[0]['symbol']}[/]"

    con.print(
        Panel(
            Text.from_markup(content),
            title=f"[bold]Top Symbols[/]  [dim]({n_traded} traded)[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


# ── Behavior ────────────────────────────────────────────────────────


def _behavior_pairs(data: dict) -> list[tuple[str, str]]:
    d = data
    pairs: list[tuple[str, str]] = []
    _maybe_add_category(pairs, "Pre-System", d, "pre_system_trades", "pre_system_win_rate")
    _maybe_add_category(pairs, "Systematic", d, "signal_trades", "signal_win_rate")
    _maybe_add_category(pairs, "Discretionary", d, "discretionary_trades", "discretionary_win_rate")

    avg_hold = d.get("avg_hold_days", 0.0)
    longest = d.get("longest_hold_days", 0)
    if avg_hold > 0 or longest > 0:
        pairs.append(("Avg Hold", f"{avg_hold:.1f}d"))
        sym = d.get("longest_hold_symbol", "")
        pairs.append(("Longest Hold", f"{longest}d {sym}" if sym else f"{longest}d"))

    return pairs


def _maybe_add_category(
    pairs: list[tuple[str, str]],
    label: str,
    data: dict,
    count_key: str,
    wr_key: str,
) -> None:
    count = data.get(count_key, 0)
    if count > 0:
        wr = data.get(wr_key, 0.0)
        pairs.append((f"{label} Trades", str(count)))
        pairs.append((f"{label} Win Rate", _pct(wr)))


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

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        click.echo(f"error: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout)

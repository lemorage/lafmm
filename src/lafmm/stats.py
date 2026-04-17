"""Beautiful terminal stats display for LAFMM trading performance."""

import json
import subprocess
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val == 0:
        return ""
    filled = int(abs(value) / max_val * width)
    char = "█"
    if value >= 0:
        return f"[green]{char * filled}[/]"
    return f"[red]{char * filled}[/]"


def _pnl_color(value: float) -> str:
    if value > 0:
        return f"[green]+${value:,.2f}[/]"
    if value < 0:
        return f"[red]-${abs(value):,.2f}[/]"
    return "$0.00"


def _pct_color(value: float) -> str:
    if value > 0:
        return f"[green]+{value:.1f}%[/]"
    if value < 0:
        return f"[red]{value:.1f}%[/]"
    return "0.0%"


def render_stats(data: dict, console: Console | None = None) -> None:
    con = console or Console()

    con.print()
    con.print(
        Panel(
            f"[bold]{data['first_date']} → {data['last_date']}[/]"
            f"  ({data['market_days']} market days, {data['active_days']} active)"
            + (f"  [dim]period: {data['period']}[/]" if data.get("period", "all") != "all" else ""),
            title="[bold]LAFMM Trading Stats[/]",
            border_style="blue",
        )
    )

    for render in (
        _render_performance,
        _render_capital,
        _render_risk,
        _render_costs,
        _render_behavior,
        _render_symbols,
        _render_monthly,
    ):
        render(data, con)
        con.print()


def _render_performance(data: dict, con: Console) -> None:
    table = Table(title="Performance", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total Trades", str(data["total_trades"]))
    table.add_row("Buys / Sells", f"{data['buys']} / {data['sells']}")
    table.add_row("Limit Orders", str(data["limit_orders"]))
    table.add_row("Market Orders", str(data["market_orders"]))
    table.add_row("Stop Orders", str(data["stop_orders"]))
    table.add_section()
    table.add_row("Wins / Losses", f"{data['wins']} / {data['losses']}")
    table.add_row("Win Rate", _pct_color(data["win_rate"]))
    table.add_row("Total P&L", _pnl_color(data["total_pnl"]))
    table.add_row("Avg Win", _pnl_color(data["avg_win"]))
    table.add_row("Avg Loss", _pnl_color(data["avg_loss"]))
    table.add_row("Largest Win", _pnl_color(data["largest_win"]))
    table.add_row("Largest Loss", _pnl_color(data["largest_loss"]))
    table.add_row("Expectancy", _pnl_color(data["expectancy"]))

    con.print(table)


def _render_capital(data: dict, con: Console) -> None:
    table = Table(title="Capital", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Start", f"${data['start_capital']:,.2f}")
    table.add_row("End", f"${data['end_capital']:,.2f}")
    table.add_row("Deposits", f"${data['total_deposits']:,.2f}")
    table.add_row("Withdrawals", f"${data['total_withdrawals']:,.2f}")
    table.add_row("Trading Return", _pct_color(data["trading_return_pct"]))

    if data.get("spy_return_pct") is not None:
        table.add_row("SPY Return", _pct_color(data["spy_return_pct"]))
        diff = data["trading_return_pct"] - data["spy_return_pct"]
        table.add_row("vs SPY", _pct_color(diff))

    con.print(table)


def _render_risk(data: dict, con: Console) -> None:
    table = Table(title="Risk", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Max Drawdown", f"[red]{data['max_drawdown_pct']:.1f}%[/]")
    table.add_row("Drawdown Days", str(data["max_drawdown_days"]))
    table.add_row("Win Streak", f"[green]{data['longest_win_streak']}[/]")
    table.add_row("Loss Streak", f"[red]{data['longest_loss_streak']}[/]")
    table.add_row("Sharpe Ratio", f"{data['sharpe']:.2f}")

    con.print(table)


def _render_costs(data: dict, con: Console) -> None:
    table = Table(title="Costs & Income", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Trading Fees", f"[red]${data['total_fees']:,.2f}[/]")
    table.add_row("Fees % of P&L", f"{data['fees_pct_of_pnl']:.1f}%")
    table.add_row("Platform Fees", f"[red]${data.get('total_platform_fees', 0):,.2f}[/]")
    table.add_row("Dividends", f"[green]${data['total_dividends']:,.2f}[/]")
    table.add_row("Tax Withheld", f"[red]${data['total_tax']:,.2f}[/]")
    table.add_row("Net Interest", _pnl_color(data["total_interest"]))

    con.print(table)


def _render_behavior(data: dict, con: Console) -> None:
    table = Table(title="Behavior", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Category", style="bold")
    table.add_column("Trades", justify="right")
    table.add_column("Win Rate", justify="right")

    pre = data.get("pre_system_trades", 0)
    if pre > 0:
        table.add_row("Pre-System", str(pre), _pct_color(data.get("pre_system_win_rate", 0)))
    sig = data["signal_trades"]
    if sig > 0:
        table.add_row("Systematic", str(sig), _pct_color(data["signal_win_rate"]))
    disc = data["impulse_trades"]
    if disc > 0:
        table.add_row("Discretionary", str(disc), _pct_color(data["impulse_win_rate"]))

    con.print(table)


def _render_symbols(data: dict, con: Console) -> None:
    symbols = data.get("top_symbols", [])
    if not symbols:
        return

    table = Table(title="Top Symbols by P&L", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Symbol", style="bold")
    table.add_column("P&L", justify="right")
    table.add_column("", width=22)

    max_abs = max(abs(s["pnl"]) for s in symbols) if symbols else 1.0
    for s in symbols:
        table.add_row(
            s["symbol"],
            _pnl_color(s["pnl"]),
            Text.from_markup(_bar(s["pnl"], max_abs)),
        )

    con.print(table)


def _render_monthly(data: dict, con: Console) -> None:
    months = data.get("monthly_pnl", [])
    if not months:
        return

    table = Table(title="Monthly P&L", box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Month", style="bold")
    table.add_column("P&L", justify="right")
    table.add_column("", width=22)

    max_abs = max(abs(m["pnl"]) for m in months) if months else 1.0
    for m in months:
        table.add_row(
            m["month"],
            _pnl_color(m["pnl"]),
            Text.from_markup(_bar(m["pnl"], max_abs)),
        )

    con.print(table)


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

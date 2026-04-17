#!/usr/bin/env python3
"""Compute trading statistics from LAFMM account data.

Usage:
    python compute.py ACCOUNT_DIR [--period PERIOD] [--benchmark PRICE_DIR]

Period formats:
    (none)              all data
    2026                year
    2026-Q1             quarter
    2026-03             month
    2026-03-01:2026-04-13  custom range
    30d                 last N days

Outputs JSON to stdout.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import tomllib
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

# ── Types ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Trade:
    date: str
    time: str
    symbol: str
    side: str
    qty: int
    price: float
    fees: float
    order: str
    pnl: float
    open_close: str
    signal: str


@dataclass(frozen=True, slots=True)
class DayEntry:
    date: str
    capital: float | None
    cash_flows: tuple[str, ...]
    trades: tuple[Trade, ...]


@dataclass(frozen=True, slots=True)
class SymbolPnl:
    symbol: str
    pnl: float


@dataclass(frozen=True, slots=True)
class MonthPnl:
    month: str
    pnl: float


@dataclass(frozen=True, slots=True)
class Stats:
    first_date: str = ""
    last_date: str = ""
    period: str = "all"
    market_days: int = 0
    active_days: int = 0
    total_trades: int = 0
    buys: int = 0
    sells: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    expectancy: float = 0.0
    start_capital: float = 0.0
    end_capital: float = 0.0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    total_fees: float = 0.0
    total_dividends: float = 0.0
    total_tax: float = 0.0
    total_interest: float = 0.0
    total_platform_fees: float = 0.0
    trading_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_days: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    sharpe: float = 0.0
    fees_pct_of_pnl: float = 0.0
    signal_trades: int = 0
    impulse_trades: int = 0
    pre_system_trades: int = 0
    signal_win_rate: float = 0.0
    impulse_win_rate: float = 0.0
    pre_system_win_rate: float = 0.0
    limit_orders: int = 0
    market_orders: int = 0
    stop_orders: int = 0
    symbols_traded: int = 0
    top_symbols: tuple[SymbolPnl, ...] = ()
    monthly_pnl: tuple[MonthPnl, ...] = ()
    spy_return_pct: float | None = None


# ── Period ───────────────────────────────────────────────────────────

QUARTER_RANGES = {
    "Q1": ("01-01", "03-31"),
    "Q2": ("04-01", "06-30"),
    "Q3": ("07-01", "09-30"),
    "Q4": ("10-01", "12-31"),
}


def parse_period(period: str | None) -> tuple[str, str] | None:
    if not period:
        return None
    if re.match(r"^\d{4}$", period):
        return (f"{period}-01-01", f"{period}-12-31")
    if re.match(r"^\d{4}-Q[1-4]$", period):
        year, q = period.split("-")
        start_md, end_md = QUARTER_RANGES[q]
        return (f"{year}-{start_md}", f"{year}-{end_md}")
    if re.match(r"^\d{4}-\d{2}$", period):
        return (f"{period}-01", f"{period}-31")
    if re.match(r"^\d+d$", period):
        days = int(period[:-1])
        end = date.today()
        start = end - timedelta(days=days)
        return (start.isoformat(), end.isoformat())
    if ":" in period:
        parts = period.split(":")
        if len(parts) == 2:
            return (parts[0], parts[1])
    print(f"error: unknown period format: {period}", file=sys.stderr)
    sys.exit(1)


def _filter_by_period(
    entries: list[DayEntry],
    capitals: list[tuple[str, float]],
    date_range: tuple[str, str],
) -> tuple[list[DayEntry], list[tuple[str, float]]]:
    start, end = date_range
    return (
        [e for e in entries if start <= e.date <= end],
        [(d, c) for d, c in capitals if start <= d <= end],
    )


# ── Parsing ──────────────────────────────────────────────────────────


def load_capital(capital_dir: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    if not capital_dir.exists():
        return rows
    for csv_file in sorted(capital_dir.glob("*.csv")):
        with csv_file.open() as f:
            for row in csv.DictReader(f):
                rows.append((row["date"], float(row["capital"])))
    rows.sort(key=lambda r: r[0])
    return rows


def parse_journal(journal_dir: Path) -> list[DayEntry]:
    entries: list[DayEntry] = []
    for year_dir in sorted(journal_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        for md_file in sorted(year_dir.glob("*.md")):
            entry = _parse_day(year_dir.name, md_file)
            if entry:
                entries.append(entry)
    return entries


def _parse_day(year: str, path: Path) -> DayEntry | None:
    text = path.read_text()
    stem = path.stem
    d = f"{year}-{stem[:2]}-{stem[3:]}"

    capital = None
    cap_match = re.search(r"Capital:\s*\$([0-9,.-]+)", text)
    if cap_match:
        capital = float(cap_match.group(1).replace(",", ""))

    cash_flows = tuple(
        line
        for line in text.splitlines()
        if re.match(r"^(Deposit|Withdrawal|Dividend|Tax|Interest|Fee):", line)
    )

    return DayEntry(
        date=d,
        capital=capital,
        cash_flows=cash_flows,
        trades=tuple(_parse_trades(d, text)),
    )


def _parse_trades(d: str, text: str) -> list[Trade]:
    trades: list[Trade] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| time "):
            in_table = True
            continue
        if line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) < 10:
                continue
            pnl_str = parts[7]
            trades.append(
                Trade(
                    date=d,
                    time=parts[0],
                    symbol=parts[1],
                    side=parts[2],
                    qty=int(parts[3]),
                    price=float(parts[4]),
                    fees=float(parts[5]),
                    order=parts[6],
                    pnl=float(pnl_str) if pnl_str != "—" else 0.0,
                    open_close=parts[8],
                    signal=parts[9],
                )
            )
        elif in_table and not line.startswith("|"):
            in_table = False
    return trades


# ── Computation ──────────────────────────────────────────────────────


def compute(
    entries: list[DayEntry],
    capitals: list[tuple[str, float]],
    period_label: str = "all",
    benchmark_dir: Path | None = None,
    tracked_since: str = "",
) -> Stats:
    if not entries:
        return Stats()

    all_trades = [t for e in entries for t in e.trades]
    closes = [t for t in all_trades if t.open_close == "C" and t.pnl != 0.0]
    capitals = [(d, c) for d, c in capitals if c > 0] or capitals

    first = capitals[0][0] if capitals else entries[0].date
    last = capitals[-1][0] if capitals else entries[-1].date

    return Stats(
        first_date=first,
        last_date=last,
        period=period_label,
        market_days=len(capitals) if capitals else len(entries),
        active_days=len(entries),
        **_performance(all_trades, closes),
        **_capital_and_flows(entries, capitals),
        **_risk(capitals, closes),
        **_costs(all_trades, closes),
        **_behavior(all_trades, closes, tracked_since),
        **_exposure(closes),
        spy_return_pct=_benchmark(benchmark_dir, first, last) if benchmark_dir else None,
    )


def _performance(all_trades: list[Trade], closes: list[Trade]) -> dict:
    wins = [t for t in closes if t.pnl > 0]
    losses = [t for t in closes if t.pnl < 0]
    total_pnl = sum(t.pnl for t in closes)
    return {
        "total_trades": len(all_trades),
        "buys": sum(1 for t in all_trades if t.side == "buy"),
        "sells": sum(1 for t in all_trades if t.side == "sell"),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(closes) - len(wins) - len(losses),
        "win_rate": len(wins) / len(closes) * 100 if closes else 0.0,
        "total_pnl": total_pnl,
        "avg_win": sum(t.pnl for t in wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(t.pnl for t in losses) / len(losses) if losses else 0.0,
        "largest_win": max((t.pnl for t in wins), default=0.0),
        "largest_loss": min((t.pnl for t in losses), default=0.0),
        "expectancy": total_pnl / len(closes) if closes else 0.0,
    }


def _sum_cash_flows(
    entries: list[DayEntry],
    first_funded: str,
) -> tuple[dict[str, float], list[tuple[str, float]]]:
    totals: dict[str, float] = defaultdict(float)
    flow_events: list[tuple[str, float]] = []

    for e in entries:
        for cf in e.cash_flows:
            usd = _extract_usd(cf)
            is_negative = ": -" in cf

            if cf.startswith("Deposit"):
                if e.date <= first_funded:
                    continue
                totals["deposits"] += usd
                flow_events.append((e.date, usd))
            elif cf.startswith("Withdrawal"):
                totals["withdrawals"] += usd
                flow_events.append((e.date, -usd))
            elif cf.startswith("Dividend"):
                totals["dividends"] += usd
            elif cf.startswith("Tax"):
                totals["tax"] += usd
            elif cf.startswith("Interest"):
                totals["interest"] += -usd if is_negative else usd
            elif cf.startswith("Fee"):
                totals["platform_fees"] += usd

    return dict(totals), flow_events


def _capital_and_flows(
    entries: list[DayEntry],
    capitals: list[tuple[str, float]],
) -> dict:
    start = capitals[0][1] if capitals else 0.0
    end = capitals[-1][1] if capitals else 0.0
    first_funded = capitals[0][0] if capitals else ""

    flows, flow_events = _sum_cash_flows(entries, first_funded)
    if start == 0 and flows.get("deposits", 0) > 0 and capitals:
        start = capitals[0][1]

    twr = _compute_twr(capitals, flow_events) if len(capitals) >= 2 else 0.0

    return {
        "start_capital": start,
        "end_capital": end,
        "total_deposits": flows.get("deposits", 0.0),
        "total_withdrawals": flows.get("withdrawals", 0.0),
        "total_dividends": flows.get("dividends", 0.0),
        "total_tax": flows.get("tax", 0.0),
        "total_interest": flows.get("interest", 0.0),
        "total_platform_fees": flows.get("platform_fees", 0.0),
        "trading_return_pct": twr,
    }


def _risk(capitals: list[tuple[str, float]], closes: list[Trade]) -> dict:
    dd_pct, dd_days = _compute_drawdown(capitals) if len(capitals) >= 2 else (0.0, 0)
    win_streak, loss_streak = _compute_streaks(closes) if closes else (0, 0)
    return {
        "max_drawdown_pct": dd_pct,
        "max_drawdown_days": dd_days,
        "longest_win_streak": win_streak,
        "longest_loss_streak": loss_streak,
        "sharpe": _compute_sharpe(capitals) if len(capitals) >= 10 else 0.0,
    }


def _costs(all_trades: list[Trade], closes: list[Trade]) -> dict:
    total_fees = sum(t.fees for t in all_trades)
    total_pnl = sum(t.pnl for t in closes)
    return {
        "total_fees": total_fees,
        "fees_pct_of_pnl": total_fees / abs(total_pnl) * 100 if total_pnl else 0.0,
    }


def _behavior(
    all_trades: list[Trade],
    closes: list[Trade],
    tracked_since: str,
) -> dict:
    post_system = [t for t in closes if t.date >= tracked_since] if tracked_since else closes
    pre_system = [t for t in closes if t.date < tracked_since] if tracked_since else []
    signal = [t for t in post_system if t.signal != "—"]
    impulse = [t for t in post_system if t.signal == "—"]
    return {
        "signal_trades": len(signal),
        "impulse_trades": len(impulse),
        "pre_system_trades": len(pre_system),
        "signal_win_rate": (
            sum(1 for t in signal if t.pnl > 0) / len(signal) * 100 if signal else 0.0
        ),
        "impulse_win_rate": (
            sum(1 for t in impulse if t.pnl > 0) / len(impulse) * 100 if impulse else 0.0
        ),
        "pre_system_win_rate": (
            sum(1 for t in pre_system if t.pnl > 0) / len(pre_system) * 100
            if pre_system
            else 0.0
        ),
        "limit_orders": sum(1 for t in all_trades if t.order == "limit"),
        "market_orders": sum(1 for t in all_trades if t.order == "market"),
        "stop_orders": sum(1 for t in all_trades if t.order == "stop"),
    }


def _exposure(closes: list[Trade]) -> dict:
    by_symbol: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    for t in closes:
        by_symbol[t.symbol] += t.pnl
        by_month[t.date[:7]] += t.pnl

    return {
        "symbols_traded": len(by_symbol),
        "top_symbols": tuple(
            SymbolPnl(sym, round(pnl, 2))
            for sym, pnl in sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
        "monthly_pnl": tuple(MonthPnl(m, round(p, 2)) for m, p in sorted(by_month.items())),
    }


# ── Helpers ──────────────────────────────────────────────────────────


def _extract_usd(line: str) -> float:
    usd_match = re.search(r"\(USD ([0-9,]+\.?\d*)\)", line)
    if usd_match:
        return float(usd_match.group(1).replace(",", ""))
    after_colon = line.split(":", 1)[1].strip() if ":" in line else ""
    num_match = re.search(r"([0-9,]+\.?\d*)", after_colon)
    return float(num_match.group(1).replace(",", "")) if num_match else 0.0


def _compute_twr(
    capitals: list[tuple[str, float]],
    flow_events: list[tuple[str, float]],
) -> float:
    if len(capitals) < 2:
        return 0.0

    flows_by_date: dict[str, float] = defaultdict(float)
    for d, amt in flow_events:
        flows_by_date[d] += amt

    cap_by_date = dict(capitals)
    flow_dates = sorted(d for d in flows_by_date if d in cap_by_date)

    # TWR: split at each flow date
    # period ends at flow date's closing NAV (pre-flow)
    # next period starts at flow date's NAV + flow amount
    compound = 1.0
    period_start = capitals[0][1]

    for flow_date in flow_dates:
        pre_flow = cap_by_date[flow_date]
        if period_start > 0:
            compound *= pre_flow / period_start
        period_start = pre_flow + flows_by_date[flow_date]

    if period_start > 0:
        compound *= capitals[-1][1] / period_start

    return round((compound - 1) * 100, 2)


def _compute_drawdown(capitals: list[tuple[str, float]]) -> tuple[float, int]:
    peak = capitals[0][1]
    max_dd = 0.0
    max_dd_days = 0
    dd_start = 0
    for i, (_, cap) in enumerate(capitals):
        if cap > peak:
            peak = cap
            dd_start = i
        dd = (peak - cap) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_days = i - dd_start
    return round(max_dd, 2), max_dd_days


def _compute_streaks(closes: list[Trade]) -> tuple[int, int]:
    max_win = max_loss = cur_win = cur_loss = 0
    for t in closes:
        if t.pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        elif t.pnl < 0:
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)
        else:
            cur_win = cur_loss = 0
    return max_win, max_loss


def _compute_sharpe(capitals: list[tuple[str, float]]) -> float:
    returns = [
        (capitals[i][1] - capitals[i - 1][1]) / capitals[i - 1][1]
        for i in range(1, len(capitals))
        if capitals[i - 1][1] > 0
    ]
    if len(returns) < 2:
        return 0.0
    avg = sum(returns) / len(returns)
    var = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    std = var**0.5
    return round(avg / std * (252**0.5), 2) if std > 0 else 0.0


def _benchmark(price_dir: Path, start: str, end: str) -> float | None:
    prices: list[tuple[str, float]] = []
    for csv_file in sorted(price_dir.glob("*.csv")):
        with csv_file.open() as f:
            prices.extend(
                (row["date"], float(row["close"]))
                for row in csv.DictReader(f)
                if start <= row["date"] <= end
            )
    if len(prices) < 2:
        return None
    prices.sort()
    return round((prices[-1][1] / prices[0][1] - 1) * 100, 2)


def _read_tracked_since(account_dir: Path) -> str:
    toml_path = account_dir / "account.toml"
    if not toml_path.exists():
        return ""
    with toml_path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tracked_since", "") or data.get("broker", {}).get("tracked_since", "")


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "usage: compute.py ACCOUNT_DIR [--period PERIOD] [--benchmark PRICE_DIR]",
            file=sys.stderr,
        )
        sys.exit(1)

    account_dir = Path(sys.argv[1])
    period_str = None
    benchmark_dir = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--period" and i + 1 < len(args):
            period_str = args[i + 1]
            i += 2
        elif args[i] == "--benchmark" and i + 1 < len(args):
            benchmark_dir = Path(args[i + 1])
            i += 2
        else:
            i += 1

    tracked_since = _read_tracked_since(account_dir)
    entries = parse_journal(account_dir / "journal")
    capitals = load_capital(account_dir / "capital")

    date_range = parse_period(period_str)
    if date_range:
        entries, capitals = _filter_by_period(entries, capitals, date_range)

    stats = compute(entries, capitals, period_str or "all", benchmark_dir, tracked_since)
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    main()

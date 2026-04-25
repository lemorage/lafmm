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
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
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
class RoundTrip:
    symbol: str
    pnl: float
    signal: str
    close_date: str


@dataclass(frozen=True, slots=True)
class SymbolPnl:
    symbol: str
    pnl: float


@dataclass(frozen=True, slots=True)
class MonthPnl:
    month: str
    pnl: float


@dataclass(frozen=True, slots=True)
class Robustness:
    excluded: str = ""
    reason: str = ""
    round_trips: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0


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
    round_trips: int = 0
    open_positions: int = 0
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
    profit_factor: float = 0.0
    concentration_pct: float = 0.0
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
    discretionary_trades: int = 0
    pre_system_trades: int = 0
    signal_win_rate: float = 0.0
    discretionary_win_rate: float = 0.0
    pre_system_win_rate: float = 0.0
    order_types: dict[str, int] = field(default_factory=dict)
    avg_hold_days: float = 0.0
    longest_hold_days: int = 0
    longest_hold_symbol: str = ""
    symbols_traded: int = 0
    top_symbols: tuple[SymbolPnl, ...] = ()
    monthly_pnl: tuple[MonthPnl, ...] = ()
    robustness: tuple[Robustness, ...] = ()
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
    trips = _round_trips(all_trades)
    grouped = _group_by_symbol(trips)
    capitals = [(d, c) for d, c in capitals if c > 0] or capitals

    first = capitals[0][0] if capitals else entries[0].date
    last = capitals[-1][0] if capitals else entries[-1].date

    capital_data, flow_events = _capital_and_flows(entries, capitals)

    return Stats(
        first_date=first,
        last_date=last,
        period=period_label,
        market_days=len(capitals) if capitals else len(entries),
        active_days=len(entries),
        open_positions=_count_open_positions(all_trades),
        **_performance(all_trades, closes, trips),
        **capital_data,
        **_risk(capitals, trips, flow_events),
        **_costs(all_trades, closes),
        **_behavior(all_trades, trips, tracked_since),
        **_exposure(closes),
        robustness=_robustness(trips, grouped),
        spy_return_pct=_benchmark(benchmark_dir, first, last) if benchmark_dir else None,
    )


def _walk_positions(
    trades: Sequence[Trade],
) -> Iterator[tuple[str, str, str, Sequence[Trade]]]:
    sorted_trades = sorted(trades, key=lambda t: (t.date, t.time))
    positions: dict[str, int] = defaultdict(int)
    open_dates: dict[str, str] = {}
    open_trades: dict[str, list[Trade]] = defaultdict(list)

    for t in sorted_trades:
        prev = positions[t.symbol]
        positions[t.symbol] += t.qty if t.side == "buy" else -t.qty

        if prev == 0 and positions[t.symbol] != 0:
            open_dates[t.symbol] = t.date
        if t.open_close == "C":
            open_trades[t.symbol].append(t)

        if positions[t.symbol] == 0 and t.symbol in open_dates:
            yield t.symbol, open_dates[t.symbol], t.date, open_trades.pop(t.symbol, [])
            del open_dates[t.symbol]


def _round_trips(trades: Sequence[Trade]) -> list[RoundTrip]:
    trips: list[RoundTrip] = []
    for symbol, _, close_date, closes in _walk_positions(trades):
        pnl = sum(c.pnl for c in closes)
        signal = closes[0].signal if closes else "—"
        trips.append(RoundTrip(symbol=symbol, pnl=pnl, signal=signal, close_date=close_date))
    return trips


def _count_open_positions(trades: Sequence[Trade]) -> int:
    positions: dict[str, int] = defaultdict(int)
    for t in sorted(trades, key=lambda t: (t.date, t.time)):
        positions[t.symbol] += t.qty if t.side == "buy" else -t.qty
    return sum(1 for qty in positions.values() if qty != 0)


def _performance(
    all_trades: Sequence[Trade],
    closes: Sequence[Trade],
    trips: Sequence[RoundTrip],
) -> dict:
    wins = [r for r in trips if r.pnl > 0]
    losses = [r for r in trips if r.pnl < 0]
    total_pnl = sum(t.pnl for t in closes)
    gross_win = sum(r.pnl for r in wins)
    gross_loss = abs(sum(r.pnl for r in losses))
    closed_pnl = gross_win - gross_loss
    return {
        "total_trades": len(all_trades),
        "buys": sum(1 for t in all_trades if t.side == "buy"),
        "sells": sum(1 for t in all_trades if t.side == "sell"),
        "round_trips": len(trips),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(trips) - len(wins) - len(losses),
        "win_rate": len(wins) / len(trips) * 100 if trips else 0.0,
        "total_pnl": total_pnl,
        "avg_win": gross_win / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "largest_win": max((r.pnl for r in wins), default=0.0),
        "largest_loss": min((r.pnl for r in losses), default=0.0),
        "expectancy": closed_pnl / len(trips) if trips else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else 0.0,
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
) -> tuple[dict, list[tuple[str, float]]]:
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
    }, flow_events


def _risk(
    capitals: Sequence[tuple[str, float]],
    trips: Sequence[RoundTrip],
    flow_events: Sequence[tuple[str, float]],
) -> dict:
    returns = _flow_adjusted_returns(capitals, flow_events) if len(capitals) >= 2 else []
    dd_pct, dd_days = _compute_drawdown(returns) if returns else (0.0, 0)
    win_streak, loss_streak = _compute_streaks(trips) if trips else (0, 0)
    return {
        "max_drawdown_pct": dd_pct,
        "max_drawdown_days": dd_days,
        "longest_win_streak": win_streak,
        "longest_loss_streak": loss_streak,
        "sharpe": _compute_sharpe_from_returns(returns) if len(returns) >= 10 else 0.0,
    }


def _costs(all_trades: list[Trade], closes: list[Trade]) -> dict:
    total_fees = sum(t.fees for t in all_trades)
    total_pnl = sum(t.pnl for t in closes)
    return {
        "total_fees": total_fees,
        "fees_pct_of_pnl": total_fees / abs(total_pnl) * 100 if total_pnl else 0.0,
    }


def _category_win_rate(trips: Sequence[RoundTrip]) -> float:
    return sum(1 for r in trips if r.pnl > 0) / len(trips) * 100 if trips else 0.0


def _behavior(
    all_trades: Sequence[Trade],
    trips: Sequence[RoundTrip],
    tracked_since: str,
) -> dict:
    if tracked_since:
        pre_system = [r for r in trips if r.close_date < tracked_since]
        post_system = [r for r in trips if r.close_date >= tracked_since]
    else:
        pre_system = []
        post_system = list(trips)
    signal = [r for r in post_system if r.signal != "—"]
    discretionary = [r for r in post_system if r.signal == "—"]
    return {
        "signal_trades": len(signal),
        "discretionary_trades": len(discretionary),
        "pre_system_trades": len(pre_system),
        "signal_win_rate": _category_win_rate(signal),
        "discretionary_win_rate": _category_win_rate(discretionary),
        "pre_system_win_rate": _category_win_rate(pre_system),
        "order_types": dict(_count_order_types(all_trades)),
        **_hold_stats(all_trades),
    }


def _exposure(closes: list[Trade]) -> dict:
    by_symbol: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    for t in closes:
        by_symbol[t.symbol] += t.pnl
        by_month[t.date[:7]] += t.pnl

    gross_abs = sum(abs(v) for v in by_symbol.values())
    top_pnl = max(abs(v) for v in by_symbol.values()) if by_symbol else 0.0
    concentration = top_pnl / gross_abs * 100 if gross_abs > 0 else 0.0

    return {
        "symbols_traded": len(by_symbol),
        "concentration_pct": round(concentration, 1),
        "top_symbols": tuple(
            SymbolPnl(sym, round(pnl, 2))
            for sym, pnl in sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
        "monthly_pnl": tuple(MonthPnl(m, round(p, 2)) for m, p in sorted(by_month.items())),
    }


def _group_by_symbol(
    trips: Sequence[RoundTrip],
) -> dict[str, list[RoundTrip]]:
    trips_by_symbol: dict[str, list[RoundTrip]] = defaultdict(list)
    for r in trips:
        trips_by_symbol[r.symbol].append(r)
    return dict(trips_by_symbol)


def _metrics_from_trips(
    trips: Sequence[RoundTrip],
    excluded: str,
    reason: str,
) -> Robustness:
    remaining = [r for r in trips if r.symbol != excluded]
    if not remaining:
        return Robustness(excluded=excluded, reason=reason)
    wins = [r for r in remaining if r.pnl > 0]
    losses = [r for r in remaining if r.pnl < 0]
    gross_win = sum(r.pnl for r in wins)
    gross_loss = abs(sum(r.pnl for r in losses))
    return Robustness(
        excluded=excluded,
        reason=reason,
        round_trips=len(remaining),
        wins=len(wins),
        losses=len(losses),
        win_rate=len(wins) / len(remaining) * 100,
        expectancy=(gross_win - gross_loss) / len(remaining),
        profit_factor=round(gross_win / gross_loss, 2) if gross_loss > 0 else 0.0,
    )


def _robustness(
    trips: Sequence[RoundTrip],
    trips_by_symbol: Mapping[str, Sequence[RoundTrip]],
    n_best: int = 1,
    n_worst: int = 1,
) -> tuple[Robustness, ...]:
    if len(trips_by_symbol) < 2:
        return ()
    symbols_by_pnl = sorted(
        trips_by_symbol,
        key=lambda s: sum(r.pnl for r in trips_by_symbol[s]),
    )
    already_excluded: set[str] = set()
    results: list[Robustness] = []
    for sym in reversed(symbols_by_pnl[-n_best:]):
        results.append(_metrics_from_trips(trips, sym, "best"))
        already_excluded.add(sym)
    for sym in symbols_by_pnl[:n_worst]:
        if sym not in already_excluded:
            results.append(_metrics_from_trips(trips, sym, "worst"))
    return tuple(results)


# ── Helpers ──────────────────────────────────────────────────────────


def _hold_durations(trades: Sequence[Trade]) -> list[tuple[str, int]]:
    return [
        (symbol, (date.fromisoformat(close) - date.fromisoformat(open_)).days)
        for symbol, open_, close, _ in _walk_positions(trades)
    ]


def _hold_stats(trades: Sequence[Trade]) -> dict:
    holds = _hold_durations(trades)
    if not holds:
        return {"avg_hold_days": 0.0, "longest_hold_days": 0, "longest_hold_symbol": ""}
    longest = max(holds, key=lambda h: h[1])
    avg = sum(d for _, d in holds) / len(holds)
    return {
        "avg_hold_days": round(avg, 1),
        "longest_hold_days": longest[1],
        "longest_hold_symbol": longest[0],
    }


def _count_order_types(trades: Sequence[Trade]) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    for t in trades:
        if t.order and t.order != "—":
            counts[t.order] += 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


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


def _flow_adjusted_returns(
    capitals: Sequence[tuple[str, float]],
    flow_events: Sequence[tuple[str, float]],
) -> list[float]:
    flows_by_date: dict[str, float] = defaultdict(float)
    for d, amt in flow_events:
        flows_by_date[d] += amt

    returns: list[float] = []
    prev = capitals[0][1]
    for i in range(1, len(capitals)):
        if prev <= 0:
            prev = capitals[i][1]
            continue
        cur_date, cur = capitals[i]
        if cur_date in flows_by_date:
            prev = cur
        else:
            returns.append((cur - prev) / prev)
            prev = cur
    return returns


def _compute_drawdown(returns: Sequence[float]) -> tuple[float, int]:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    max_dd_days = 0
    dd_start = 0

    for i, r in enumerate(returns):
        equity *= 1 + r
        if equity > peak:
            peak = equity
            dd_start = i
        dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_days = i - dd_start

    return round(max_dd, 2), max_dd_days


def _compute_streaks(trips: Sequence[RoundTrip]) -> tuple[int, int]:
    max_win = max_loss = cur_win = cur_loss = 0
    for r in trips:
        if r.pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        elif r.pnl < 0:
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)
        else:
            cur_win = cur_loss = 0
    return max_win, max_loss


def _compute_sharpe_from_returns(returns: Sequence[float]) -> float:
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

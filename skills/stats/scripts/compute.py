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
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
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
class Position:
    symbol: str
    side: str
    open_date: str
    close_date: str
    opens: tuple[Trade, ...]
    closes: tuple[Trade, ...]
    pnl: float
    fees: float
    signal: str
    peak_qty: int
    entry_price: float
    exit_price: float
    hold_days: int


@dataclass(frozen=True, slots=True)
class SymbolStats:
    symbol: str
    pnl: float
    round_trips: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class MonthPnl:
    month: str
    pnl: float


@dataclass(frozen=True, slots=True)
class RollingPoint:
    window: int
    trip_number: int
    win_rate: float
    expectancy: float
    profit_factor: float


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
    top_symbols: tuple[SymbolStats, ...] = ()
    monthly_pnl: tuple[MonthPnl, ...] = ()
    rolling: tuple[RollingPoint, ...] = ()
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


# ── Position building ───────────────────────────────────────────────


def _weighted_price(trades: Sequence[Trade]) -> float:
    total_qty = sum(t.qty for t in trades)
    if total_qty == 0:
        return 0.0
    return sum(t.price * t.qty for t in trades) / total_qty


def _emit_position(
    symbol: str,
    trades: Sequence[Trade],
    open_date: str,
    close_date: str,
    peak_qty: int,
) -> Position:
    opens = tuple(t for t in trades if t.open_close == "O")
    closes = tuple(t for t in trades if t.open_close == "C")
    first_open = opens[0] if opens else (closes[0] if closes else trades[0])
    return Position(
        symbol=symbol,
        side="long" if first_open.side == "buy" else "short",
        open_date=open_date,
        close_date=close_date,
        opens=opens,
        closes=closes,
        pnl=sum(c.pnl for c in closes),
        fees=sum(t.fees for t in trades),
        signal=opens[0].signal if opens else "—",
        peak_qty=peak_qty,
        entry_price=_weighted_price(opens) if opens else 0.0,
        exit_price=_weighted_price(closes) if closes else 0.0,
        hold_days=(date.fromisoformat(close_date) - date.fromisoformat(open_date)).days,
    )


def build_positions(
    trades: Sequence[Trade],
) -> tuple[tuple[Position, ...], int]:
    sorted_trades = sorted(trades, key=lambda t: (t.date, t.time))
    qty: dict[str, int] = defaultdict(int)
    open_dates: dict[str, str] = {}
    accumulated: dict[str, list[Trade]] = defaultdict(list)
    peak: dict[str, int] = defaultdict(int)
    positions: list[Position] = []

    for trade in sorted_trades:
        if trade.qty == 0:
            continue
        symbol = trade.symbol
        old_qty = qty[symbol]
        delta = trade.qty if trade.side == "buy" else -trade.qty
        new_qty = old_qty + delta

        if old_qty == 0:
            open_dates[symbol] = trade.date
            accumulated[symbol] = [trade]
            peak[symbol] = abs(new_qty)
            qty[symbol] = new_qty
            continue

        same_sign = (old_qty > 0 and new_qty > 0) or (old_qty < 0 and new_qty < 0)

        if same_sign:
            accumulated[symbol].append(trade)
            peak[symbol] = max(peak[symbol], abs(new_qty))
            qty[symbol] = new_qty
            continue

        if new_qty == 0:
            accumulated[symbol].append(trade)
            positions.append(
                _emit_position(
                    symbol, accumulated[symbol], open_dates[symbol], trade.date, peak[symbol]
                )
            )
            del open_dates[symbol]
            del accumulated[symbol]
            del peak[symbol]
            qty[symbol] = 0
            continue

        # sign crossing (flip): split trade into close + open portions
        close_qty = abs(old_qty)
        open_qty = abs(new_qty)
        ratio = close_qty / trade.qty
        close_part = replace(
            trade,
            qty=close_qty,
            open_close="C",
            pnl=round(trade.pnl * ratio, 2) if trade.pnl else 0.0,
            fees=round(trade.fees * ratio, 2),
        )
        open_part = replace(
            trade,
            qty=open_qty,
            open_close="O",
            pnl=0.0,
            fees=round(trade.fees * (1 - ratio), 2),
        )
        accumulated[symbol].append(close_part)
        positions.append(
            _emit_position(
                symbol, accumulated[symbol], open_dates[symbol], trade.date, peak[symbol]
            )
        )
        open_dates[symbol] = trade.date
        accumulated[symbol] = [open_part]
        peak[symbol] = open_qty
        qty[symbol] = new_qty

    open_count = sum(1 for q in qty.values() if q != 0)
    return tuple(positions), open_count


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
    positions, open_count = build_positions(all_trades)
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
        open_positions=open_count,
        **_performance(all_trades, positions),
        **capital_data,
        **_risk(capitals, positions, flow_events),
        **_costs(all_trades, positions),
        **_behavior(all_trades, positions, tracked_since),
        **_exposure(positions),
        rolling=_rolling(positions),
        robustness=_robustness(positions),
        spy_return_pct=_benchmark(benchmark_dir, first, last) if benchmark_dir else None,
    )


def _performance(
    all_trades: Sequence[Trade],
    positions: Sequence[Position],
) -> dict:
    wins = [p for p in positions if p.pnl > 0]
    losses = [p for p in positions if p.pnl < 0]
    total_pnl = sum(p.pnl for p in positions)
    gross_win = sum(p.pnl for p in wins)
    gross_loss = abs(sum(p.pnl for p in losses))
    return {
        "total_trades": len(all_trades),
        "buys": sum(1 for t in all_trades if t.side == "buy"),
        "sells": sum(1 for t in all_trades if t.side == "sell"),
        "round_trips": len(positions),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(positions) - len(wins) - len(losses),
        "win_rate": len(wins) / len(positions) * 100 if positions else 0.0,
        "total_pnl": total_pnl,
        "avg_win": gross_win / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "largest_win": max((p.pnl for p in wins), default=0.0),
        "largest_loss": min((p.pnl for p in losses), default=0.0),
        "expectancy": total_pnl / len(positions) if positions else 0.0,
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
    positions: Sequence[Position],
    flow_events: Sequence[tuple[str, float]],
) -> dict:
    returns = _flow_adjusted_returns(capitals, flow_events) if len(capitals) >= 2 else []
    dd_pct, dd_days = _compute_drawdown(returns) if returns else (0.0, 0)
    win_streak, loss_streak = _compute_streaks(positions) if positions else (0, 0)
    return {
        "max_drawdown_pct": dd_pct,
        "max_drawdown_days": dd_days,
        "longest_win_streak": win_streak,
        "longest_loss_streak": loss_streak,
        "sharpe": _compute_sharpe_from_returns(returns) if len(returns) >= 10 else 0.0,
    }


def _costs(all_trades: Sequence[Trade], positions: Sequence[Position]) -> dict:
    total_fees = sum(t.fees for t in all_trades)
    total_pnl = sum(p.pnl for p in positions)
    return {
        "total_fees": total_fees,
        "fees_pct_of_pnl": total_fees / abs(total_pnl) * 100 if total_pnl else 0.0,
    }


def _category_win_rate(positions: Sequence[Position]) -> float:
    return sum(1 for p in positions if p.pnl > 0) / len(positions) * 100 if positions else 0.0


def _behavior(
    all_trades: Sequence[Trade],
    positions: Sequence[Position],
    tracked_since: str,
) -> dict:
    if tracked_since:
        pre_system = [p for p in positions if p.close_date < tracked_since]
        post_system = [p for p in positions if p.close_date >= tracked_since]
    else:
        pre_system = []
        post_system = list(positions)
    signal = [p for p in post_system if p.signal != "—"]
    discretionary = [p for p in post_system if p.signal == "—"]

    holds = [(p.symbol, p.hold_days) for p in positions]
    if holds:
        longest = max(holds, key=lambda h: h[1])
        avg_hold = round(sum(d for _, d in holds) / len(holds), 1)
        hold_stats = {
            "avg_hold_days": avg_hold,
            "longest_hold_days": longest[1],
            "longest_hold_symbol": longest[0],
        }
    else:
        hold_stats = {"avg_hold_days": 0.0, "longest_hold_days": 0, "longest_hold_symbol": ""}

    return {
        "signal_trades": len(signal),
        "discretionary_trades": len(discretionary),
        "pre_system_trades": len(pre_system),
        "signal_win_rate": _category_win_rate(signal),
        "discretionary_win_rate": _category_win_rate(discretionary),
        "pre_system_win_rate": _category_win_rate(pre_system),
        "order_types": dict(_count_order_types(all_trades)),
        **hold_stats,
    }


def _exposure(positions: Sequence[Position]) -> dict:
    by_symbol: dict[str, list[Position]] = defaultdict(list)
    by_month: dict[str, float] = defaultdict(float)
    for p in positions:
        by_symbol[p.symbol].append(p)
        for close in p.closes:
            by_month[close.date[:7]] += close.pnl

    symbol_pnl = {s: sum(p.pnl for p in ps) for s, ps in by_symbol.items()}
    gross_abs = sum(abs(v) for v in symbol_pnl.values())
    top_pnl = max(abs(v) for v in symbol_pnl.values()) if symbol_pnl else 0.0
    concentration = top_pnl / gross_abs * 100 if gross_abs > 0 else 0.0

    top: list[SymbolStats] = []
    for symbol, pnl in sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)[:10]:
        symbol_positions = by_symbol[symbol]
        trip_count = len(symbol_positions)
        win_count = sum(1 for p in symbol_positions if p.pnl > 0)
        loss_count = sum(1 for p in symbol_positions if p.pnl < 0)
        top.append(
            SymbolStats(
                symbol=symbol,
                pnl=round(pnl, 2),
                round_trips=trip_count,
                wins=win_count,
                losses=loss_count,
                win_rate=round(win_count / trip_count * 100, 1) if trip_count else 0.0,
            )
        )

    return {
        "symbols_traded": len(by_symbol),
        "concentration_pct": round(concentration, 1),
        "top_symbols": tuple(top),
        "monthly_pnl": tuple(MonthPnl(m, round(p, 2)) for m, p in sorted(by_month.items())),
    }


def _rolling(
    positions: Sequence[Position],
    window: int = 10,
) -> tuple[RollingPoint, ...]:
    if len(positions) < window:
        return ()
    points: list[RollingPoint] = []
    for i in range(window, len(positions) + 1):
        batch = positions[i - window : i]
        wins = [p for p in batch if p.pnl > 0]
        losses = [p for p in batch if p.pnl < 0]
        gross_win = sum(p.pnl for p in wins)
        gross_loss = abs(sum(p.pnl for p in losses))
        points.append(
            RollingPoint(
                window=window,
                trip_number=i,
                win_rate=round(len(wins) / window * 100, 1),
                expectancy=round((gross_win - gross_loss) / window, 2),
                profit_factor=round(gross_win / gross_loss, 2) if gross_loss > 0 else 0.0,
            )
        )
    return tuple(points)


def _metrics_excluding(
    positions: Sequence[Position],
    excluded: str,
    reason: str,
) -> Robustness:
    remaining = [p for p in positions if p.symbol != excluded]
    if not remaining:
        return Robustness(excluded=excluded, reason=reason)
    wins = [p for p in remaining if p.pnl > 0]
    losses = [p for p in remaining if p.pnl < 0]
    gross_win = sum(p.pnl for p in wins)
    gross_loss = abs(sum(p.pnl for p in losses))
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
    positions: Sequence[Position],
    n_best: int = 1,
    n_worst: int = 1,
) -> tuple[Robustness, ...]:
    by_symbol: dict[str, float] = defaultdict(float)
    for p in positions:
        by_symbol[p.symbol] += p.pnl
    if len(by_symbol) < 2:
        return ()
    ranked = sorted(by_symbol, key=lambda s: by_symbol[s])
    already_excluded: set[str] = set()
    results: list[Robustness] = []
    for symbol in reversed(ranked[-n_best:]):
        results.append(_metrics_excluding(positions, symbol, "best"))
        already_excluded.add(symbol)
    for symbol in ranked[:n_worst]:
        if symbol not in already_excluded:
            results.append(_metrics_excluding(positions, symbol, "worst"))
    return tuple(results)


# ── Helpers ──────────────────────────────────────────────────────────


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


def _compute_streaks(positions: Sequence[Position]) -> tuple[int, int]:
    max_win = max_loss = cur_win = cur_loss = 0
    for p in positions:
        if p.pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        elif p.pnl < 0:
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

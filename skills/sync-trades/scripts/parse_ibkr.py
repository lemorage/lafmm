#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""Parse IBKR Flex Query CSV and write LAFMM journal entries.

Usage:
    uv run parse_ibkr.py CSV_FILE JOURNAL_DIR

Reads an IBKR Flex Query CSV export (with section codes enabled),
parses trades, cash flows, and NAV data, and writes year-partitioned
journal markdown files. Skips dates that already have journal entries.

Expects three IBKR sections:
  TRNT — trades (filtered to STK/OPT, forex skipped)
  CTRN — cash transactions (deposits, withdrawals, dividends)
  EQUT — net asset value (daily total account value)
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ORDER_MAP: Mapping[str, str] = {"LMT": "limit", "MKT": "market", "STP": "stop"}


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
    pnl: str
    open_close: str


@dataclass(frozen=True, slots=True)
class ImportStats:
    new_files: int
    skipped: int
    trades: int
    cash_flows: int


def parse_csv(
    csv_text: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, float]]:
    trades: list[dict[str, str]] = []
    cash: list[dict[str, str]] = []
    nav: dict[str, float] = {}
    headers: dict[str, list[str]] = {}

    for row in csv.reader(io.StringIO(csv_text)):
        if not row or not row[0]:
            continue
        if row[0] == "HEADER":
            headers[row[1]] = row[2:]
            continue
        if row[0] != "DATA" or row[1] not in headers:
            continue
        data = dict(zip(headers[row[1]], row[2:], strict=False))
        if row[1] == "TRNT":
            trades.append(data)
        elif row[1] == "CTRN":
            cash.append(data)
        elif row[1] == "EQUT":
            nav[data["ReportDate"]] = float(data["Total"])

    return trades, cash, nav


def _parse_time(dt: str) -> str:
    tp = dt.split(";")[1] if ";" in dt else ""
    return f"{tp[:2]}:{tp[2:4]}" if len(tp) >= 4 else "--:--"


def normalize_trade(raw: dict[str, str]) -> Trade | None:
    if raw.get("AssetClass") == "CASH":
        return None
    pnl_str = raw.get("FifoPnlRealized", "").strip()
    pnl_raw = float(pnl_str) if pnl_str else 0.0
    return Trade(
        date=raw["TradeDate"],
        time=_parse_time(raw["DateTime"]),
        symbol=raw["Symbol"],
        side="buy" if raw["Buy/Sell"] == "BUY" else "sell",
        qty=abs(int(raw["Quantity"])),
        price=float(raw["TradePrice"]),
        fees=abs(float(raw["IBCommission"])),
        order=ORDER_MAP.get(raw["OrderType"], raw["OrderType"].lower() or "—"),
        pnl=f"{pnl_raw:+.2f}" if pnl_raw != 0 else "—",
        open_close=raw["Open/CloseIndicator"].strip() or "—",
    )


def normalize_trades(raw: Sequence[dict[str, str]]) -> Sequence[Trade]:
    return [t for r in raw if (t := normalize_trade(r)) is not None]


def normalize_cash(raw: Sequence[dict[str, str]]) -> dict[str, list[str]]:
    by_date: dict[str, list[str]] = defaultdict(list)
    for c in raw:
        dt = c["Date/Time"]
        date_part = dt.split(";")[0] if ";" in dt else dt
        amount = float(c["Amount"])
        ccy = c["CurrencyPrimary"]
        symbol = c.get("Symbol", "")
        typ = c["Type"]

        if "Deposit" in typ or "Withdrawal" in typ:
            label = "Deposit" if amount > 0 else "Withdrawal"
            sign = "+" if amount > 0 else "-"
            by_date[date_part].append(f"{label}: {sign}{ccy} {abs(amount):,.2f}")
        elif "Dividend" in typ:
            sym = f" ({symbol})" if symbol else ""
            by_date[date_part].append(f"Dividend: +{ccy} {amount:.2f}{sym}")

    return dict(by_date)


def _format_trade_row(trade: Trade) -> str:
    return (
        f"| {trade.time} | {trade.symbol} | {trade.side} "
        f"| {trade.qty} | {trade.price:.2f} | {trade.fees:.2f} "
        f"| {trade.order} | {trade.pnl} | {trade.open_close} | — |"
    )


def _format_day(
    date_str: str,
    day_trades: Sequence[Trade],
    cash_lines: Sequence[str],
    nav_value: float | None,
) -> str:
    year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
    lines = [f"# {year}/{month}-{day}", ""]

    lines.append(f"Capital: ${nav_value:,.2f}" if nav_value else "Capital: —")
    lines.extend(cash_lines)
    lines.append("")

    if day_trades:
        lines.append("## Trades")
        lines.append("")
        lines.append(
            "| time | symbol | side | qty | price | fees | order | pnl | open_close | signal |"
        )
        lines.append(
            "|------|--------|------|-----|-------|------|-------|-----|------------|--------|"
        )
        lines.extend(_format_trade_row(t) for t in day_trades)
        lines.append("")

    lines.append("## Observations")
    lines.append("")
    return "\n".join(lines)


def write_journal(
    journal_dir: Path,
    trades: Sequence[Trade],
    cash: dict[str, list[str]],
    nav: dict[str, float],
) -> ImportStats:
    trades_by_date: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        trades_by_date[t.date].append(t)

    all_dates = sorted(set(list(trades_by_date.keys()) + list(cash.keys())))
    new_files = 0
    skipped = 0
    trade_count = 0
    cash_count = 0

    for date_str in all_dates:
        year = date_str[:4]
        year_dir = journal_dir / year
        year_dir.mkdir(parents=True, exist_ok=True)
        file_path = year_dir / f"{date_str[4:6]}-{date_str[6:8]}.md"

        if file_path.exists():
            skipped += 1
            continue

        day_trades = trades_by_date.get(date_str, [])
        cash_lines = cash.get(date_str, [])
        content = _format_day(date_str, day_trades, cash_lines, nav.get(date_str))
        file_path.write_text(content)

        new_files += 1
        trade_count += len(day_trades)
        cash_count += len(cash_lines)

    return ImportStats(
        new_files=new_files,
        skipped=skipped,
        trades=trade_count,
        cash_flows=cash_count,
    )


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: parse_ibkr.py CSV_FILE JOURNAL_DIR", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    journal_dir = Path(sys.argv[2])

    csv_text = csv_path.read_text()
    raw_trades, raw_cash, nav = parse_csv(csv_text)
    trades = normalize_trades(raw_trades)
    cash = normalize_cash(raw_cash)
    stats = write_journal(journal_dir, trades, cash, nav)

    forex = len(raw_trades) - len(trades)
    date_range = ""
    if trades:
        dates = sorted({t.date for t in trades})
        date_range = f" ({dates[0]} → {dates[-1]})"

    print(
        json.dumps(
            {
                "trades": stats.trades,
                "new_files": stats.new_files,
                "skipped": stats.skipped,
                "cash_flows": stats.cash_flows,
                "forex_filtered": forex,
                "date_range": date_range.strip(),
            }
        )
    )


if __name__ == "__main__":
    main()

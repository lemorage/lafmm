#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""Parse IBKR Flex Query CSV and write LAFMM journal entries.

Usage:
    uv run parse_ibkr.py CSV_FILE ACCOUNT_DIR

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
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ORDER_MAP: Mapping[str, str] = {"LMT": "limit", "MKT": "market", "STP": "stop"}

_SIGNAL_RE = re.compile(
    r"^\s*-\s+\*\*(BUY|SELL|DANGER: Up Over|DANGER: Dn Over|WATCH)\*\*"
    r"\s+\$[\d.]+\s+Rule\s+((?:9|10)\([a-f]\))"
    r"\s+—\s+.+\((\d{4}-\d{2}-\d{2})\)\s*$"
)

_SIGNAL_SHORT: Mapping[str, str] = {
    "BUY": "BUY",
    "SELL": "SELL",
    "DANGER: Up Over": "DANGER",
    "DANGER: Dn Over": "DANGER",
    "WATCH": "WATCH",
}

type SignalIndex = Mapping[str, Sequence[tuple[str, str]]]


def load_signal_index(cache_dir: Path) -> SignalIndex:
    if not cache_dir.is_dir():
        return {}
    index: dict[str, list[tuple[str, str]]] = {}
    for md in cache_dir.rglob("*.md"):
        if md.name in ("group.md", "market.md"):
            continue
        symbol = md.stem
        signals: list[tuple[str, str]] = []
        for line in md.read_text().splitlines():
            m = _SIGNAL_RE.match(line)
            if m:
                label = f"{_SIGNAL_SHORT[m.group(1)]} {m.group(2)}"
                signals.append((m.group(3), label))
        if signals:
            index[symbol] = sorted(signals, key=lambda s: s[0])
    return index


_SKIP_PREFIXES = frozenset({"WATCH", "DANGER"})


def _compact_to_iso(date_str: str) -> str:
    if len(date_str) == 8 and "-" not in date_str:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def lookup_signal(
    index: SignalIndex,
    symbol: str,
    trade_date: str,
    trade_side: str,
) -> str:
    signals = index.get(symbol, ())
    if not signals:
        return "—"
    trade_date_iso = _compact_to_iso(trade_date)
    is_buy = trade_side == "buy"
    for signal_date, label in reversed(signals):
        if signal_date >= trade_date_iso:
            continue
        prefix = label.split()[0] if label else ""
        if prefix in _SKIP_PREFIXES:
            continue
        if (prefix == "BUY" and is_buy) or (prefix == "SELL" and not is_buy):
            return label
        # Signal direction contradicts trade direction — stop searching.
        return "—"
    return "—"


JOURNAL_README = """\
# Journal

## File convention

One file per trading day: `{YEAR}/{MM-DD}.md`

## Format

Each file starts with a capital snapshot, then a trades table, then observations.

### Capital

```
Capital: $52,340.00
```

Total account value for that day (cash + positions), in base currency,
from broker export.

On days with non-trading cash movements, lines below Capital show the
original currency:

```
Capital: $6,893.96
Deposit: +HKD 46,550.00
```

```
Capital: $73,250.00
Deposit: +$20,000.00
Dividend: +$150.00 (GOOG)
Tax: -$22.50 (GOOG)
Interest: +$4.23
Fee: -$10.00
```

Line types:
- **Deposit/Withdrawal**: cash transfers in/out
- **Dividend**: stock dividends
- **Tax**: withholding tax on dividends
- **Interest**: broker interest received (+) or margin interest paid (-)
- **Fee**: data fees, platform fees

Capital is always base currency. Cash flow lines show original currency,
which may differ for international transfers.

### Trades

| time | symbol | side | qty | price | fees | order | pnl | open_close | signal |
|------|--------|------|-----|-------|------|-------|-----|------------|--------|

- **time**: HH:MM local, or `--:--`
- **symbol**: ticker, uppercase
- **side**: `buy` or `sell`
- **qty**: shares, or `2c` for contracts
- **price**: fill price
- **fees**: commission + fees
- **order**: `market`, `limit`, `stop`, or `—`
- **pnl**: realized P&L from broker. `—` on opens.
- **open_close**: `O` (opening), `C` (closing), or `—`
- **signal**: most recent matching Livermore signal before trade date (BUY for buys, SELL for sells), or `—` if none or contradicting

### Observations

Freeform text below trades. What you saw, felt, learned.

## Import

The `sync-trades` skill writes daily files in this format.
Drop your broker CSV and tell the agent to import it.
"""


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
        fx_rate = float(c.get("FXRateToBase", "1") or "1")
        usd_amount = abs(amount * fx_rate)
        usd_suffix = f" (USD {usd_amount:,.2f})" if ccy != "USD" else ""

        if "Deposit" in typ or "Withdrawal" in typ:
            label = "Deposit" if amount > 0 else "Withdrawal"
            sign = "+" if amount > 0 else "-"
            by_date[date_part].append(f"{label}: {sign}{ccy} {abs(amount):,.2f}{usd_suffix}")
        elif "Dividend" in typ or "Payment in Lieu" in typ:
            sym = f" ({symbol})" if symbol else ""
            by_date[date_part].append(f"Dividend: +{ccy} {amount:.2f}{sym}")
        elif "Withholding Tax" in typ:
            sym = f" ({symbol})" if symbol else ""
            by_date[date_part].append(f"Tax: -{ccy} {abs(amount):.2f}{sym}")
        elif "Interest" in typ:
            sign = "+" if amount > 0 else "-"
            by_date[date_part].append(f"Interest: {sign}{ccy} {abs(amount):.2f}")
        elif "Fee" in typ or "Other Fee" in typ:
            by_date[date_part].append(f"Fee: -{ccy} {abs(amount):.2f}")

    return dict(by_date)


def _format_trade_row(trade: Trade, signal: str = "—") -> str:
    return (
        f"| {trade.time} | {trade.symbol} | {trade.side} "
        f"| {trade.qty} | {trade.price:.2f} | {trade.fees:.2f} "
        f"| {trade.order} | {trade.pnl} | {trade.open_close} | {signal} |"
    )


def _format_day(
    date_str: str,
    day_trades: Sequence[Trade],
    cash_lines: Sequence[str],
    nav_value: float | None,
    signals: SignalIndex | None = None,
    tracked_since: str = "",
) -> str:
    year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
    lines = [f"# {year}/{month}-{day}", ""]

    lines.append(f"Capital: ${nav_value:,.2f}" if nav_value else "Capital: —")
    lines.extend(cash_lines)
    lines.append("")

    can_fill = (
        signals is not None and tracked_since != "" and date_str >= tracked_since.replace("-", "")
    )

    if day_trades:
        lines.append("## Trades")
        lines.append("")
        lines.append(
            "| time | symbol | side | qty | price | fees | order | pnl | open_close | signal |"
        )
        lines.append(
            "|------|--------|------|-----|-------|------|-------|-----|------------|--------|"
        )
        for t in day_trades:
            sig = "—"
            if can_fill and signals is not None:
                sig = lookup_signal(signals, t.symbol, t.date, t.side)
            lines.append(_format_trade_row(t, sig))
        lines.append("")

    lines.append("## Observations")
    lines.append("")
    return "\n".join(lines)


def _ensure_journal_readme(journal_dir: Path) -> None:
    readme = journal_dir / "README.md"
    if readme.exists():
        return
    journal_dir.mkdir(parents=True, exist_ok=True)
    readme.write_text(JOURNAL_README)


def write_journal(
    journal_dir: Path,
    trades: Sequence[Trade],
    cash: dict[str, list[str]],
    nav: dict[str, float],
    signals: SignalIndex | None = None,
    tracked_since: str = "",
) -> ImportStats:
    _ensure_journal_readme(journal_dir)

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
        content = _format_day(
            date_str,
            day_trades,
            cash_lines,
            nav.get(date_str),
            signals,
            tracked_since,
        )
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


def write_capital(capital_dir: Path, nav: dict[str, float]) -> int:
    capital_dir.mkdir(parents=True, exist_ok=True)

    by_year: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for date_str, value in sorted(nav.items()):
        by_year[date_str[:4]].append((date_str, value))

    new_rows = 0
    for year, rows in sorted(by_year.items()):
        csv_path = capital_dir / f"{year}.csv"

        existing: set[str] = set()
        if csv_path.exists():
            with csv_path.open() as f:
                existing = {r["date"] for r in csv.DictReader(f)}

        new = [(d, v) for d, v in rows if _nav_date(d) not in existing]
        if not new:
            continue

        is_new = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", newline="") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["date", "capital"])
            for d, v in new:
                writer.writerow([_nav_date(d), f"{v:.2f}"])
                new_rows += 1

    return new_rows


def _nav_date(d: str) -> str:
    return _compact_to_iso(d)


def _read_tracked_since(account_dir: Path) -> str:
    toml_path = account_dir / "account.toml"
    if not toml_path.exists():
        return ""
    for line in toml_path.read_text().splitlines():
        if line.strip().startswith("tracked_since"):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            return val
    return ""


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: parse_ibkr.py CSV_FILE ACCOUNT_DIR", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    account_dir = Path(sys.argv[2])
    journal_dir = account_dir / "journal"
    capital_dir = account_dir / "capital"
    cache_dir = account_dir.parent / "cache"

    signals = load_signal_index(cache_dir)
    tracked_since = _read_tracked_since(account_dir)

    csv_text = csv_path.read_text()
    raw_trades, raw_cash, nav = parse_csv(csv_text)
    trades = normalize_trades(raw_trades)
    cash = normalize_cash(raw_cash)
    stats = write_journal(journal_dir, trades, cash, nav, signals, tracked_since)
    capital_rows = write_capital(capital_dir, nav)

    forex = len(raw_trades) - len(trades)
    date_range = ""
    if trades:
        dates = sorted({t.date for t in trades})
        date_range = f"({dates[0]} → {dates[-1]})"

    print(
        json.dumps(
            {
                "trades": stats.trades,
                "new_files": stats.new_files,
                "skipped": stats.skipped,
                "cash_flows": stats.cash_flows,
                "forex_filtered": forex,
                "capital_rows": capital_rows,
                "date_range": date_range.strip(),
            }
        )
    )


if __name__ == "__main__":
    main()

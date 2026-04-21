from __future__ import annotations

import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

_MAX_DATE_LABELS = 6


@dataclass(frozen=True)
class OHLCV:
    dates: tuple[str, ...]
    opens: tuple[float, ...]
    highs: tuple[float, ...]
    lows: tuple[float, ...]
    closes: tuple[float, ...]
    volumes: tuple[float, ...]


@dataclass(frozen=True)
class ChartOpts:
    group: str | None = None
    period: str = "90d"
    width: int = 80
    height: int = 24
    title: str | None = None
    ma: tuple[str, ...] = ()
    fast: int = 12
    slow: int = 26
    signal: int = 9
    rsi_period: int = 14
    bb_period: int = 20
    bb_width: float = 2.0
    k: int = 14
    d: int = 3
    adx_period: int = 14
    wr_period: int = 14
    cci_period: int = 20
    vol_period: int = 20


def render_chart_cmd(
    data_dir: Path, chart_type: str, ticker: str, opts: ChartOpts,
) -> None:
    ticker_dir = _resolve_ticker(data_dir, ticker, opts.group)
    if ticker_dir is None:
        return

    raw = _load_ohlcv(ticker_dir)
    if not raw.dates:
        print(f"no price data in {ticker_dir}", file=sys.stderr)
        return

    filtered = _filter_period(raw, opts.period)
    if not filtered.dates:
        print("no data in the requested period", file=sys.stderr)
        return

    title = opts.title or _auto_title(ticker, chart_type, filtered, opts)
    x_labels = _date_labels(filtered.dates)

    output = _dispatch(chart_type, filtered, opts, title, x_labels)
    if output is not None:
        print(output)


# ── Ticker resolution ───────────────────────────────────────────────


def _resolve_ticker(
    data_dir: Path, ticker: str, group: str | None,
) -> Path | None:
    ticker = ticker.upper()

    if group:
        path = data_dir / group / ticker
        if path.is_dir():
            return path
        print(f"{ticker} not found in {group}/", file=sys.stderr)
        return None

    matches = [
        d / ticker
        for d in sorted(data_dir.iterdir())
        if d.is_dir() and (d / ticker).is_dir()
    ]

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        groups = [m.parent.name for m in matches]
        print(f"{ticker} found in multiple groups: {', '.join(groups)}", file=sys.stderr)
        print("  use --group to disambiguate", file=sys.stderr)
        return None

    print(f"{ticker} not found in any group under {data_dir}", file=sys.stderr)
    return None


# ── OHLCV loading ───────────────────────────────────────────────────


def _load_ohlcv(ticker_dir: Path) -> OHLCV:
    rows: list[tuple[str, float, float, float, float, float]] = []
    for csv_file in sorted(ticker_dir.glob("*.csv")):
        with csv_file.open() as f:
            for row in csv.DictReader(f):
                rows.append((
                    row["date"],
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                ))
    rows.sort(key=lambda r: r[0])
    if not rows:
        return OHLCV((), (), (), (), (), ())
    dates, opens, highs, lows, closes, volumes = zip(*rows, strict=True)
    return OHLCV(dates, opens, highs, lows, closes, volumes)


# ── Period filtering ────────────────────────────────────────────────


def _filter_period(data: OHLCV, period: str) -> OHLCV:
    start, end = _parse_period(period)
    indices = [i for i, d in enumerate(data.dates) if start <= d <= end]
    if not indices:
        return OHLCV((), (), (), (), (), ())
    start, end = indices[0], indices[-1] + 1
    return OHLCV(
        data.dates[start:end], data.opens[start:end], data.highs[start:end],
        data.lows[start:end], data.closes[start:end], data.volumes[start:end],
    )


def _parse_period(period: str) -> tuple[str, str]:
    today = date.today()

    if period.endswith("d"):
        days = int(period[:-1])
        return (str(today - timedelta(days=days)), str(today))
    if period.endswith("y"):
        years = int(period[:-1])
        return (str(today.replace(year=today.year - years)), str(today))

    if len(period) == 4 and period.isdigit():
        return (f"{period}-01-01", f"{period}-12-31")

    if "-Q" in period:
        year, q = period.split("-Q")
        q = int(q)
        starts = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
        ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
        return (f"{year}-{starts[q]}", f"{year}-{ends[q]}")

    if ":" in period:
        parts = period.split(":")
        return (parts[0], parts[1])

    if len(period) == 7:
        return (f"{period}-01", f"{period}-31")

    return ("0000-01-01", "9999-12-31")


# ── Auto title and labels ──────────────────────────────────────────


def _auto_title(
    ticker: str, chart_type: str, data: OHLCV, opts: ChartOpts,
) -> str:
    date_range = f"{data.dates[0]} to {data.dates[-1]}"
    type_label = _type_label(chart_type, opts)
    return f"{ticker} — {type_label}  ({date_range})"


def _type_label(chart_type: str, opts: ChartOpts) -> str:
    match chart_type:
        case "macd":
            return f"MACD ({opts.fast}/{opts.slow}/{opts.signal})"
        case "rsi":
            return f"RSI ({opts.rsi_period})"
        case "bollinger":
            return f"Bollinger ({opts.bb_period}, {opts.bb_width})"
        case "stochastic":
            return f"Stochastic ({opts.k}/{opts.d})"
        case "adx":
            return f"ADX ({opts.adx_period})"
        case "williams-r" | "williams_r":
            return f"Williams %R ({opts.wr_period})"
        case "cci":
            return f"CCI ({opts.cci_period})"
        case "volume":
            return f"Volume (RVOL {opts.vol_period})"
        case "overlay":
            return f"Overlay ({', '.join(opts.ma)})" if opts.ma else "Overlay"
        case _:
            return chart_type.replace("-", " ").title()


def _date_labels(dates: Sequence[str]) -> tuple[str, ...]:
    if len(dates) <= 1:
        return tuple(dates)
    n = len(dates)
    count = min(_MAX_DATE_LABELS, n)
    step = max(1, (n - 1) // (count - 1)) if count > 1 else 1
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return tuple(_short_date(dates[i]) for i in indices)


def _short_date(d: str) -> str:
    parts = d.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    return d


# ── Dispatch to composers ──────────────────────────────────────────


_CHART_TYPES = {
    "line", "candle", "macd", "rsi", "overlay", "bollinger",
    "stochastic", "adx", "williams-r", "cci", "obv", "vwap", "volume",
}


def _dispatch(
    chart_type: str,
    data: OHLCV,
    opts: ChartOpts,
    title: str,
    x_labels: tuple[str, ...],
) -> str | None:
    from lafmm.chart import (
        adx_chart,
        bollinger_chart,
        candlestick_chart,
        cci_chart,
        line_chart,
        macd_chart,
        obv_chart,
        overlay_chart,
        rsi_chart,
        stochastic_chart,
        volume_chart,
        vwap_chart,
        williams_r_chart,
    )

    layout = {"width": opts.width, "height": opts.height, "title": title, "x_labels": x_labels}
    closes, highs, lows, volumes = data.closes, data.highs, data.lows, data.volumes

    match chart_type:
        case "line":
            return line_chart(closes, **layout)
        case "candle":
            return candlestick_chart(data.opens, highs, lows, closes, **layout)
        case "macd":
            return macd_chart(
                closes, fast=opts.fast, slow=opts.slow, signal=opts.signal, **layout,
            )
        case "rsi":
            return rsi_chart(closes, period=opts.rsi_period, **layout)
        case "overlay":
            overlays = _parse_ma_flags(opts.ma)
            return overlay_chart(closes, overlays=overlays, **layout)
        case "bollinger":
            return bollinger_chart(
                closes, period=opts.bb_period, band_width=opts.bb_width, **layout,
            )
        case "stochastic":
            return stochastic_chart(
                highs, lows, closes, k_period=opts.k, d_period=opts.d, **layout,
            )
        case "adx":
            return adx_chart(highs, lows, closes, period=opts.adx_period, **layout)
        case "williams-r" | "williams_r":
            return williams_r_chart(highs, lows, closes, period=opts.wr_period, **layout)
        case "cci":
            return cci_chart(highs, lows, closes, period=opts.cci_period, **layout)
        case "obv":
            return obv_chart(closes, volumes, **layout)
        case "vwap":
            return vwap_chart(highs, lows, closes, volumes, **layout)
        case "volume":
            return volume_chart(closes, volumes, period=opts.vol_period, **layout)
        case _:
            types = ", ".join(sorted(_CHART_TYPES))
            print(f"unknown chart type: {chart_type}", file=sys.stderr)
            print(f"  available: {types}", file=sys.stderr)
            return None


def _parse_ma_flags(ma_flags: Sequence[str]) -> tuple[tuple[str, int], ...]:
    result: list[tuple[str, int]] = []
    for flag in ma_flags:
        if ":" in flag:
            kind, period = flag.split(":", 1)
            result.append((kind, int(period)))
    return tuple(result)

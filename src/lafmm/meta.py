from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

import yfinance as yf


@dataclass(frozen=True, slots=True)
class TickerIdentity:
    fetched: str
    long_name: str
    sector: str
    industry: str
    quote_type: str


@dataclass(frozen=True, slots=True)
class TickerSnapshot:
    fetched: str
    market_cap: int
    beta: float
    average_volume: int
    short_ratio: float
    short_percent_of_float: float
    fifty_two_week_high: float
    fifty_two_week_low: float


@dataclass(frozen=True, slots=True)
class TickerMeta:
    symbol: str
    identity: TickerIdentity
    snapshot: TickerSnapshot


_META_DIR = "_meta"


def _write_ticker_meta(data_dir: Path, meta: TickerMeta) -> None:
    meta_dir = data_dir / _META_DIR
    meta_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": meta.symbol,
        "identity": {
            "fetched": meta.identity.fetched,
            "long_name": meta.identity.long_name,
            "sector": meta.identity.sector,
            "industry": meta.identity.industry,
            "quote_type": meta.identity.quote_type,
        },
        "snapshot": {
            "fetched": meta.snapshot.fetched,
            "market_cap": meta.snapshot.market_cap,
            "beta": meta.snapshot.beta,
            "average_volume": meta.snapshot.average_volume,
            "short_ratio": meta.snapshot.short_ratio,
            "short_percent_of_float": meta.snapshot.short_percent_of_float,
            "fifty_two_week_high": meta.snapshot.fifty_two_week_high,
            "fifty_two_week_low": meta.snapshot.fifty_two_week_low,
        },
    }
    json_path = meta_dir / f"{meta.symbol}.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_ticker_meta(data_dir: Path, symbol: str) -> TickerMeta | None:
    json_path = data_dir / _META_DIR / f"{symbol}.json"
    if not json_path.exists():
        return None
    raw = json.loads(json_path.read_text())
    return _parse_ticker_meta(raw)


type _StrDict = dict[str, str | int | float]


def _parse_ticker_meta(raw: dict[str, object]) -> TickerMeta:
    ident = cast(_StrDict, raw["identity"])
    snap = cast(_StrDict, raw["snapshot"])
    return TickerMeta(
        symbol=str(raw["symbol"]),
        identity=TickerIdentity(
            fetched=str(ident["fetched"]),
            long_name=str(ident["long_name"]),
            sector=str(ident["sector"]),
            industry=str(ident["industry"]),
            quote_type=str(ident["quote_type"]),
        ),
        snapshot=TickerSnapshot(
            fetched=str(snap["fetched"]),
            market_cap=int(snap["market_cap"]),
            beta=float(snap["beta"]),
            average_volume=int(snap["average_volume"]),
            short_ratio=float(snap["short_ratio"]),
            short_percent_of_float=float(snap["short_percent_of_float"]),
            fifty_two_week_high=float(snap["fifty_two_week_high"]),
            fifty_two_week_low=float(snap["fifty_two_week_low"]),
        ),
    )


def fetch_ticker_meta(symbol: str) -> TickerMeta | None:
    info = _fetch_info(symbol)
    if not info or "sector" not in info:
        return None
    today = date.today().isoformat()
    return TickerMeta(
        symbol=symbol,
        identity=_build_identity(info, today),
        snapshot=_build_snapshot(info, today),
    )


def _fetch_info(symbol: str) -> _StrDict:
    try:
        return cast(_StrDict, yf.Ticker(symbol).info)
    except Exception:
        print(f"meta {symbol}: yfinance lookup failed", file=sys.stderr)
        return {}


def _build_identity(info: _StrDict, today: str) -> TickerIdentity:
    return TickerIdentity(
        fetched=today,
        long_name=str(info.get("longName", "")),
        sector=str(info.get("sector", "")),
        industry=str(info.get("industry", "")),
        quote_type=str(info.get("quoteType", "")),
    )


def _build_snapshot(info: _StrDict, today: str) -> TickerSnapshot:
    return TickerSnapshot(
        fetched=today,
        market_cap=int(info.get("marketCap", 0)),
        beta=float(info.get("beta", 0)),
        average_volume=int(info.get("averageVolume", 0)),
        short_ratio=float(info.get("shortRatio", 0)),
        short_percent_of_float=float(info.get("shortPercentOfFloat", 0)),
        fifty_two_week_high=float(info.get("fiftyTwoWeekHigh", 0)),
        fifty_two_week_low=float(info.get("fiftyTwoWeekLow", 0)),
    )


SNAPSHOT_MAX_AGE_DAYS = 30


def ensure_ticker_meta(
    data_dir: Path,
    symbol: str,
    snapshot_max_age_days: int = SNAPSHOT_MAX_AGE_DAYS,
) -> TickerMeta | None:
    existing = load_ticker_meta(data_dir, symbol)
    if existing is None:
        return _fetch_and_write(data_dir, symbol)
    if _snapshot_is_stale(existing.snapshot, snapshot_max_age_days):
        return _refresh_snapshot(data_dir, existing)
    return existing


def _snapshot_is_stale(snapshot: TickerSnapshot, max_age_days: int) -> bool:
    fetched = date.fromisoformat(snapshot.fetched)
    age = (date.today() - fetched).days
    return age > max_age_days


def _fetch_and_write(data_dir: Path, symbol: str) -> TickerMeta | None:
    meta = fetch_ticker_meta(symbol)
    if meta is None:
        return None
    _write_ticker_meta(data_dir, meta)
    return meta


def _refresh_snapshot(data_dir: Path, existing: TickerMeta) -> TickerMeta:
    info = _fetch_info(existing.symbol)
    if not info:
        return existing
    refreshed = TickerMeta(
        symbol=existing.symbol,
        identity=existing.identity,
        snapshot=_build_snapshot(info, date.today().isoformat()),
    )
    _write_ticker_meta(data_dir, refreshed)
    return refreshed

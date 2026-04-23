import csv
import tomllib
from collections.abc import Sequence
from pathlib import Path

from lafmm.group import init_group
from lafmm.models import Col, GroupConfig, GroupState, MarketState
from lafmm.quant.types import PriceSeries


def load_price_series(ticker_dir: Path) -> PriceSeries | None:
    dates: list[str] = []
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[int] = []
    for csv_file in sorted(ticker_dir.glob("*.csv")):
        with csv_file.open() as f:
            for row in csv.DictReader(f):
                dates.append(row["date"])
                opens.append(float(row["open"]))
                highs.append(float(row["high"]))
                lows.append(float(row["low"]))
                closes.append(float(row["close"]))
                volumes.append(int(row["volume"]))
    if not dates:
        return None
    order = sorted(range(len(dates)), key=lambda i: dates[i])
    return PriceSeries(
        dates=tuple(dates[i] for i in order),
        open=tuple(opens[i] for i in order),
        high=tuple(highs[i] for i in order),
        low=tuple(lows[i] for i in order),
        close=tuple(closes[i] for i in order),
        volume=tuple(volumes[i] for i in order),
    )


def load_prices(ticker_dir: Path) -> Sequence[tuple[str, float]]:
    series = load_price_series(ticker_dir)
    if series is None:
        return []
    return list(zip(series.dates, series.close, strict=True))


def load_group_config(folder: Path) -> GroupConfig:
    toml_path = folder / "group.toml"
    with toml_path.open("rb") as f:
        raw = tomllib.load(f)
    return GroupConfig(
        name=raw.get("name", folder.name),
        leaders=(raw["leaders"][0], raw["leaders"][1]),
        swing_pct=float(raw.get("swing_pct", 5.0)),
        confirm_pct=float(raw.get("confirm_pct", 2.5)),
        start_col=Col[raw.get("start_col", "UT")],
    )


def load_group(folder: Path) -> GroupState:
    config = load_group_config(folder)

    prices: dict[str, Sequence[tuple[str, float]]] = {}
    for child in sorted(folder.iterdir()):
        if child.is_dir() and (rows := load_prices(child)):
            prices[child.name.upper()] = rows

    return init_group(config, prices)


def load_market(root: Path) -> MarketState:
    groups: list[GroupState] = []
    for folder in sorted(root.iterdir()):
        if folder.is_dir() and (folder / "group.toml").exists():
            groups.append(load_group(folder))
    return MarketState(groups=tuple(groups))

import csv
import tomllib
from pathlib import Path

from lafmm.group import init_group
from lafmm.models import Col, GroupConfig, GroupState, MarketState


def load_prices(ticker_dir: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for csv_file in sorted(ticker_dir.glob("*.csv")):
        with csv_file.open() as f:
            reader = csv.DictReader(f)
            rows.extend((row["date"], float(row["price"])) for row in reader)
    rows.sort(key=lambda r: r[0])
    return rows


def load_group(folder: Path) -> GroupState:
    toml_path = folder / "group.toml"
    with toml_path.open("rb") as f:
        raw = tomllib.load(f)

    leaders = (raw["leaders"][0], raw["leaders"][1])
    start_col = Col[raw.get("start_col", "UT")]
    config = GroupConfig(
        name=raw.get("name", folder.name),
        leaders=leaders,
        swing_pct=float(raw.get("swing_pct", 6.0)),
        confirm_pct=float(raw.get("confirm_pct", 3.0)),
        start_col=start_col,
    )

    prices: dict[str, list[tuple[str, float]]] = {}
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

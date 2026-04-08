import csv
import tomllib
from pathlib import Path

from lafmm.group import init_group
from lafmm.models import Col, GroupConfig, GroupState, MarketState


def load_prices(path: Path) -> list[tuple[str, float]]:
    with path.open() as f:
        reader = csv.DictReader(f)
        return [(row["date"], float(row["price"])) for row in reader]


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
    for csv_file in sorted(folder.glob("*.csv")):
        ticker = csv_file.stem.upper()
        prices[ticker] = load_prices(csv_file)

    return init_group(config, prices)


def load_market(root: Path) -> MarketState:
    groups: list[GroupState] = []
    for folder in sorted(root.iterdir()):
        if folder.is_dir() and (folder / "group.toml").exists():
            groups.append(load_group(folder))
    return MarketState(groups=tuple(groups))

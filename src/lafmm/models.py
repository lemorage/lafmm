from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Final, Literal

# ── Column Identifiers ──────────────────────────────────────────────


class Col(Enum):
    SR = 0  # Secondary Rally       (pencil)   — Rule 6(g)
    NR = 1  # Natural Rally          (pencil)   — Rules 6(c)(d)
    UT = 2  # Upward Trend           (BLACK INK) — Rule 1
    DT = 3  # Downward Trend         (RED INK)   — Rule 2
    NREAC = 4  # Natural Reaction       (pencil)   — Rules 6(a)(b)
    SREAC = 5  # Secondary Reaction     (pencil)   — Rule 6(h)

    @property
    def label(self) -> str:
        return _COL_LABELS[self]

    @property
    def short(self) -> str:
        return _COL_SHORT[self]

    @property
    def ink(self) -> Literal["black", "red", "pencil"]:
        if self is Col.UT:
            return "black"
        if self is Col.DT:
            return "red"
        return "pencil"

    @property
    def is_confirmed_trend(self) -> bool:
        return self in (Col.UT, Col.DT)

    @property
    def is_bullish(self) -> bool:
        return self in (Col.SR, Col.NR, Col.UT)

    @property
    def is_bearish(self) -> bool:
        return self in (Col.DT, Col.NREAC, Col.SREAC)

    @property
    def continuation_direction(self) -> int:
        return 1 if self.is_bullish else -1


_COL_LABELS: Final[dict[Col, str]] = {
    Col.SR: "Secondary Rally",
    Col.NR: "Natural Rally",
    Col.UT: "Upward Trend",
    Col.DT: "Downward Trend",
    Col.NREAC: "Natural Reaction",
    Col.SREAC: "Secondary Reaction",
}

_COL_SHORT: Final[dict[Col, str]] = {
    Col.SR: "SecRally",
    Col.NR: "NatRally",
    Col.UT: "UPTREND",
    Col.DT: "DNTREND",
    Col.NREAC: "NatReac",
    Col.SREAC: "SecReac",
}

COL_ORDER: Final[tuple[Col, ...]] = (Col.SR, Col.NR, Col.UT, Col.DT, Col.NREAC, Col.SREAC)


# ── Signal Types ─────────────────────────────────────────────────────


class SignalType(Enum):
    BUY = auto()  # Rules 10(a), 10(d)
    SELL = auto()  # Rules 10(b), 10(c)
    DANGER_UP_OVER = auto()  # Rule 10(e)
    DANGER_DOWN_OVER = auto()  # Rule 10(f)
    WATCH = auto()  # Rules 9(a), 9(b), 9(c)


# ── Underline Color ──────────────────────────────────────────────────

type UnderlineColor = Literal["red", "black"]


# ── Data Records ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Entry:
    date: str
    price: float
    col: Col

    @property
    def ink(self) -> Literal["black", "red", "pencil"]:
        return self.col.ink

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")


@dataclass(frozen=True, slots=True)
class PivotalPoint:
    date: str
    price: float
    source_col: Col
    underline: UnderlineColor


@dataclass(frozen=True, slots=True)
class Signal:
    date: str
    signal_type: SignalType
    price: float
    rule: str
    detail: str
    pivot_ref: PivotalPoint | None = None


# ── Engine Configuration ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EngineConfig:
    swing: float = 6.0
    confirm: float = 3.0
    ticker: str = ""

    def __post_init__(self) -> None:
        if self.swing <= 0:
            raise ValueError(f"swing must be positive, got {self.swing}")
        if self.confirm <= 0:
            raise ValueError(f"confirm must be positive, got {self.confirm}")
        if self.confirm >= self.swing:
            raise ValueError(f"confirm ({self.confirm}) must be < swing ({self.swing})")

    @classmethod
    def for_key_price(cls, ticker: str = "KEY") -> EngineConfig:
        return cls(swing=12.0, confirm=6.0, ticker=ticker)

    @classmethod
    def for_stock(cls, ticker: str = "", swing: float = 6.0) -> EngineConfig:
        return cls(swing=swing, confirm=swing / 2.0, ticker=ticker)

    @classmethod
    def for_stock_pct(cls, ticker: str, price: float, swing_pct: float = 5.0) -> EngineConfig:
        swing = price * swing_pct / 100.0
        return cls(swing=swing, confirm=swing / 2.0, ticker=ticker)


# ── Immutable Engine State ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EngineState:
    current: Col | None = None
    last: Mapping[Col, float | None] = field(default_factory=lambda: {c: None for c in Col})
    last_pivot: Mapping[Col, PivotalPoint | None] = field(
        default_factory=lambda: {c: None for c in Col}
    )
    nr_peak: float | None = None
    nreac_trough: float | None = None
    entries: tuple[Entry, ...] = ()
    pivots: tuple[PivotalPoint, ...] = ()
    signals: tuple[Signal, ...] = ()
    emitted_keys: frozenset[tuple[str, str | None]] = frozenset()


# ── Group / Market Types ─────────────────────────────────────────────

type GroupTrend = Literal["bullish", "bearish", "neutral"]


@dataclass(frozen=True, slots=True)
class GroupConfig:
    name: str
    leaders: tuple[str, str]
    swing_pct: float = 5.0
    confirm_pct: float = 2.5
    start_col: Col = Col.UT


@dataclass(frozen=True, slots=True)
class StockState:
    ticker: str
    config: EngineConfig
    engine: EngineState
    is_leader: bool


@dataclass(frozen=True, slots=True)
class GroupState:
    config: GroupConfig
    key_price: StockState | None = None
    stocks: tuple[StockState, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketState:
    groups: tuple[GroupState, ...] = ()

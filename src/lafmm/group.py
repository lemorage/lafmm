from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Final

from lafmm.engine import process, start
from lafmm.models import (
    Col,
    EngineConfig,
    GroupConfig,
    GroupState,
    GroupTrend,
    MarketState,
    StockState,
)

MARKET_CONSENSUS_THRESHOLD: Final[float] = 0.6

# ── Group Queries ────────────────────────────────────────────────────


def group_leaders(state: GroupState) -> tuple[StockState, StockState]:
    leaders = [s for s in state.stocks if s.is_leader]
    return (leaders[0], leaders[1])


def group_tracked(state: GroupState) -> tuple[StockState, ...]:
    return tuple(s for s in state.stocks if not s.is_leader)


def group_trend(state: GroupState) -> GroupTrend:
    if state.key_price is None:
        return "neutral"
    match state.key_price.engine.current:
        case Col.UT:
            return "bullish"
        case Col.DT:
            return "bearish"
        case _:
            return "neutral"


# ── Market Queries ───────────────────────────────────────────────────


def market_trend(state: MarketState) -> GroupTrend:
    if not state.groups:
        return "neutral"
    bullish = sum(1 for g in state.groups if group_trend(g) == "bullish")
    bearish = sum(1 for g in state.groups if group_trend(g) == "bearish")
    total = len(state.groups)
    threshold = total * MARKET_CONSENSUS_THRESHOLD
    if bullish > threshold:
        return "bullish"
    if bearish > threshold:
        return "bearish"
    return "neutral"


# ── Initialization ───────────────────────────────────────────────────


def init_stock(
    ticker: str,
    first_date: str,
    first_price: float,
    swing_pct: float,
    start_col: Col,
    is_leader: bool,
) -> StockState:
    cfg = EngineConfig.for_stock_pct(ticker, first_price, swing_pct)
    engine = start(start_col, first_date, first_price)
    return StockState(ticker=ticker, config=cfg, engine=engine, is_leader=is_leader)


def _init_key_price(
    config: GroupConfig,
    a_prices: Sequence[tuple[str, float]],
    b_prices: Sequence[tuple[str, float]],
) -> StockState:
    a_by_date = dict(a_prices)
    b_by_date = dict(b_prices)
    all_dates = sorted(a_by_date.keys() & b_by_date.keys())

    ticker = f"{config.leaders[0]}+{config.leaders[1]}"
    first_combined = a_by_date[all_dates[0]] + b_by_date[all_dates[0]]
    cfg = EngineConfig.for_key_price(ticker=ticker)
    engine = start(config.start_col, all_dates[0], first_combined)

    kp = StockState(ticker=ticker, config=cfg, engine=engine, is_leader=False)
    for date in all_dates[1:]:
        combined = a_by_date[date] + b_by_date[date]
        kp = _process_stock(kp, date, combined)
    return kp


def init_group(
    config: GroupConfig,
    prices: Mapping[str, Sequence[tuple[str, float]]],
) -> GroupState:
    stocks: list[StockState] = []
    leader_prices: dict[str, Sequence[tuple[str, float]]] = {}

    for ticker, rows in prices.items():
        if not rows:
            continue
        is_leader = ticker in config.leaders
        first_date, first_price = rows[0]
        stock = init_stock(
            ticker,
            first_date,
            first_price,
            config.swing_pct,
            config.start_col,
            is_leader,
        )
        for date, price in rows[1:]:
            stock = _process_stock(stock, date, price)
        stocks.append(stock)
        if is_leader:
            leader_prices[ticker] = rows

    leaders_first = sorted(stocks, key=lambda s: (not s.is_leader, s.ticker))

    key_price = None
    a_ticker, b_ticker = config.leaders
    if a_ticker in leader_prices and b_ticker in leader_prices:
        key_price = _init_key_price(config, leader_prices[a_ticker], leader_prices[b_ticker])

    return GroupState(config=config, key_price=key_price, stocks=tuple(leaders_first))


# ── Processing ───────────────────────────────────────────────────────


def _process_stock(stock: StockState, date: str, price: float) -> StockState:
    new_engine = process(stock.engine, stock.config, date, price)
    return replace(stock, engine=new_engine)


def process_group(
    state: GroupState,
    date: str,
    prices: Mapping[str, float],
) -> GroupState:
    new_stocks = tuple(
        _process_stock(s, date, prices[s.ticker]) if s.ticker in prices else s for s in state.stocks
    )

    new_kp = state.key_price
    if new_kp is not None:
        a_ticker, b_ticker = state.config.leaders
        if a_ticker in prices and b_ticker in prices:
            combined = prices[a_ticker] + prices[b_ticker]
            new_kp = _process_stock(new_kp, date, combined)

    return replace(state, key_price=new_kp, stocks=new_stocks)


def process_market(
    state: MarketState,
    date: str,
    prices: Mapping[str, float],
) -> MarketState:
    new_groups = tuple(process_group(g, date, prices) for g in state.groups)
    return replace(state, groups=new_groups)

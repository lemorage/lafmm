from dataclasses import replace

from lafmm.models import (
    Col,
    EngineConfig,
    EngineState,
    Entry,
    PivotalPoint,
    Signal,
    SignalType,
    UnderlineColor,
)

# ── Public API ───────────────────────────────────────────────────────


def start(col: Col, date: str, price: float) -> EngineState:
    if col not in (Col.UT, Col.DT):
        raise ValueError(f"initial column must be UT or DT, got {col.name}")
    return _record(EngineState(), date, price, col)


def process(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    match state.current:
        case None:
            raise RuntimeError("not initialized — call start() first")
        case Col.UT:
            state = _from_ut(state, cfg, date, price)
        case Col.DT:
            state = _from_dt(state, cfg, date, price)
        case Col.NR:
            state = _from_nr(state, cfg, date, price)
        case Col.NREAC:
            state = _from_nreac(state, cfg, date, price)
        case Col.SR:
            state = _from_sr(state, cfg, date, price)
        case Col.SREAC:
            state = _from_sreac(state, cfg, date, price)
    return _check_signals(state, cfg, date, price)


# ── Recording Primitives ────────────────────────────────────────────


def _record(state: EngineState, date: str, price: float, col: Col) -> EngineState:
    entry = Entry(date=date, price=price, col=col)
    return replace(
        state,
        current=col,
        last={**state.last, col: price},
        entries=(*state.entries, entry),
    )


def _mark_pivot(
    state: EngineState,
    date: str,
    source_col: Col,
    underline: UnderlineColor,
) -> EngineState:
    price = state.last[source_col]
    if price is None:
        return state

    pivot = PivotalPoint(date=date, price=price, source_col=source_col, underline=underline)
    return replace(
        state,
        pivots=(*state.pivots, pivot),
        last_pivot={**state.last_pivot, source_col: pivot},
    )


def _emit(
    state: EngineState,
    date: str,
    signal_type: SignalType,
    price: float,
    rule: str,
    detail: str,
    pivot_ref: PivotalPoint | None = None,
    dedup_override: str | None = None,
) -> EngineState:
    if dedup_override is not None:
        dedup = (rule, dedup_override)
    else:
        pivot_key = f"{pivot_ref.source_col.name}:{pivot_ref.price}" if pivot_ref else None
        dedup = (rule, pivot_key)
    if dedup in state.emitted_keys:
        return state

    signal = Signal(
        date=date,
        signal_type=signal_type,
        price=price,
        rule=rule,
        detail=detail,
        pivot_ref=pivot_ref,
    )
    return replace(
        state,
        signals=(*state.signals, signal),
        emitted_keys=state.emitted_keys | {dedup},
    )


def _find_pivot(
    state: EngineState,
    source_col: Col,
    underline: UnderlineColor,
) -> PivotalPoint | None:
    piv = state.last_pivot[source_col]
    if piv is not None and piv.underline == underline:
        return piv
    return None


# ── Column Handlers ──────────────────────────────────────────────────


def _from_ut(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.UT]
    if lp is None:
        return state

    # Rule 6(a): reaction from UT
    if lp - price >= cfg.swing:
        state = _mark_pivot(state, date, Col.UT, "red")  # Rule 4(a)
        return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

    # Continuation: new high
    if price > lp:
        return _record(state, date, price, Col.UT)

    return state


def _from_dt(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.DT]
    if lp is None:
        return state

    # Rule 6(c): rally from DT
    if price - lp >= cfg.swing:
        state = _mark_pivot(state, date, Col.DT, "black")  # Rule 4(c)
        return replace(_record(state, date, price, Col.NR), nr_peak=price)

    # Continuation: new low
    if price < lp:
        return _record(state, date, price, Col.DT)

    return state


def _from_nr(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.NR]
    if lp is None:
        return state

    last_ut = state.last[Col.UT]
    last_dt = state.last[Col.DT]
    last_nreac = state.last[Col.NREAC]

    # Priority 1 — Rule 6(f): direct UT override
    if last_ut is not None and price > last_ut:
        return _record(state, date, price, Col.UT)

    # Priority 2 — Rule 5(a): pivot confirmation to UT
    nr_piv = _find_pivot(state, Col.NR, "black")
    if nr_piv is not None and price >= nr_piv.price + cfg.confirm:
        return _record(state, date, price, Col.UT)

    # Priority 3 — Reaction of ~swing: leave NR
    if lp - price >= cfg.swing:
        state = _mark_pivot(state, date, Col.NR, "black")  # Rule 4(d)

        # 3a — Rule 6(b) override: below last DT
        if last_dt is not None and price < last_dt:
            return _record(state, date, price, Col.DT)

        # 3b — Rule 6(b): below last NREAC (strict <)
        if last_nreac is not None and price < last_nreac:
            return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

        # 3c — Rule 6(h): at or above last NREAC (indecisive, "not lower than" = >=)
        if last_nreac is not None and price >= last_nreac:
            return _record(state, date, price, Col.SREAC)

        # 3d — No NREAC reference
        return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

    # Priority 4 — Continuation: new high in NR
    if price > lp:
        return replace(_record(state, date, price, Col.NR), nr_peak=price)

    return state


def _from_nreac(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.NREAC]
    if lp is None:
        return state

    last_ut = state.last[Col.UT]
    last_dt = state.last[Col.DT]
    last_nr = state.last[Col.NR]

    # Priority 1 — Rule 6(e): direct DT override
    if last_dt is not None and price < last_dt:
        return _record(state, date, price, Col.DT)

    # Priority 2 — Rule 5(b): pivot confirmation to DT
    nreac_piv = _find_pivot(state, Col.NREAC, "red")
    if nreac_piv is not None and price <= nreac_piv.price - cfg.confirm:
        return _record(state, date, price, Col.DT)

    # Priority 3 — Rally of ~swing: leave NREAC
    if price - lp >= cfg.swing:
        state = _mark_pivot(state, date, Col.NREAC, "red")  # Rule 4(b)

        # 3a — Rule 6(d) override: above last UT
        if last_ut is not None and price > last_ut:
            return _record(state, date, price, Col.UT)

        # 3b — Rule 6(d): above last NR (strict >, "exceeded")
        if last_nr is not None and price > last_nr:
            return replace(_record(state, date, price, Col.NR), nr_peak=price)

        # 3c — Rule 6(g): at or below last NR (indecisive, "did not exceed" = <=)
        if last_nr is not None and price <= last_nr:
            return _record(state, date, price, Col.SR)

        # 3d — No NR reference
        return replace(_record(state, date, price, Col.NR), nr_peak=price)

    # Priority 4 — Continuation: new low in NREAC
    if price < lp:
        return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

    return state


def _from_sr(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.SR]
    if lp is None:
        return state

    last_nr = state.last[Col.NR]
    last_ut = state.last[Col.UT]

    # Priority 1: exceeds last UT → UT directly (most extreme first)
    if last_ut is not None and price > last_ut:
        return _record(state, date, price, Col.UT)

    # Priority 2: exceeds last NR → promote to NR
    if last_nr is not None and price > last_nr:
        return replace(_record(state, date, price, Col.NR), nr_peak=price)

    # Reaction from SR: swing-sized drop
    if lp - price >= cfg.swing:
        last_dt = state.last[Col.DT]

        if last_dt is not None and price < last_dt:
            return _record(state, date, price, Col.DT)

        return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

    # Continuation: new high in SR
    if price > lp:
        return _record(state, date, price, Col.SR)

    return state


def _from_sreac(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    lp = state.last[Col.SREAC]
    if lp is None:
        return state

    last_nreac = state.last[Col.NREAC]
    last_dt = state.last[Col.DT]

    # Priority 1: below last DT → DT directly (most extreme first)
    if last_dt is not None and price < last_dt:
        return _record(state, date, price, Col.DT)

    # Priority 2: below last NREAC → demote to NREAC
    if last_nreac is not None and price < last_nreac:
        return replace(_record(state, date, price, Col.NREAC), nreac_trough=price)

    # Rally from SREAC: swing-sized rise
    if price - lp >= cfg.swing:
        last_ut = state.last[Col.UT]

        if last_ut is not None and price > last_ut:
            return _record(state, date, price, Col.UT)

        return replace(_record(state, date, price, Col.NR), nr_peak=price)

    # Continuation: new low in SREAC
    if price < lp:
        return _record(state, date, price, Col.SREAC)

    return state


# ── Signal Detection — Rules 9 & 10 ─────────────────────────────────


def _check_signals(
    state: EngineState,
    cfg: EngineConfig,
    date: str,
    price: float,
) -> EngineState:
    state = _check_10a(state, cfg, date, price)
    state = _check_10c(state, cfg, date, price)
    state = _check_10b(state, cfg, date, price)
    state = _check_10d(state, cfg, date, price)
    state = _check_10e(state, cfg, date, price)
    state = _check_10f(state, cfg, date, price)
    return state


def _check_10a(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current is not Col.UT:
        return state
    piv = _find_pivot(state, Col.UT, "red")
    if piv is None or price < piv.price + cfg.confirm:
        return state
    return _emit(
        state,
        date,
        SignalType.BUY,
        price,
        "10(a)",
        f"UT resumed: ${price:.2f} >= pivot ${piv.price:.2f} + confirm ${cfg.confirm:.1f}",
        pivot_ref=piv,
    )


def _check_10c(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current is not Col.DT:
        return state
    piv = _find_pivot(state, Col.DT, "black")
    if piv is None or price > piv.price - cfg.confirm:
        return state
    return _emit(
        state,
        date,
        SignalType.SELL,
        price,
        "10(c)",
        f"DT resumed: ${price:.2f} <= pivot ${piv.price:.2f} - confirm ${cfg.confirm:.1f}",
        pivot_ref=piv,
    )


def _check_10b(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current not in (Col.NREAC, Col.DT):
        return state
    piv = _find_pivot(state, Col.UT, "red")
    if piv is None or price > piv.price - cfg.confirm:
        return state
    return _emit(
        state,
        date,
        SignalType.SELL,
        price,
        "10(b)",
        f"UT failed: ${price:.2f} broke ${cfg.confirm:.1f}+ below UT pivot ${piv.price:.2f}",
        pivot_ref=piv,
    )


def _check_10d(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current not in (Col.NR, Col.UT):
        return state
    piv = _find_pivot(state, Col.DT, "black")
    if piv is None or price < piv.price + cfg.confirm:
        return state
    return _emit(
        state,
        date,
        SignalType.BUY,
        price,
        "10(d)",
        f"DT failed: ${price:.2f} broke ${cfg.confirm:.1f}+ above DT pivot ${piv.price:.2f}",
        pivot_ref=piv,
    )


def _check_10e(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current not in (Col.NREAC, Col.SREAC, Col.DT):
        return state
    ut_piv = _find_pivot(state, Col.UT, "red")
    if ut_piv is None or state.nr_peak is None:
        return state

    gap = ut_piv.price - state.nr_peak
    if gap <= 0 or gap > cfg.confirm:
        return state

    drop = state.nr_peak - price
    if drop < cfg.confirm:
        return state

    return _emit(
        state,
        date,
        SignalType.DANGER_UP_OVER,
        price,
        "10(e)",
        (
            f"NR peaked at ${state.nr_peak:.2f}, just ${gap:.1f} below "
            f"UT pivot ${ut_piv.price:.2f}, then reacted ${drop:.1f} — uptrend may be over"
        ),
        pivot_ref=ut_piv,
        dedup_override=f"NR_peak_{state.nr_peak}",
    )


def _check_10f(state: EngineState, cfg: EngineConfig, date: str, price: float) -> EngineState:
    if state.current not in (Col.NR, Col.SR, Col.UT):
        return state
    dt_piv = _find_pivot(state, Col.DT, "black")
    if dt_piv is None or state.nreac_trough is None:
        return state

    gap = state.nreac_trough - dt_piv.price
    if gap <= 0 or gap > cfg.confirm:
        return state

    rise = price - state.nreac_trough
    if rise < cfg.confirm:
        return state

    return _emit(
        state,
        date,
        SignalType.DANGER_DOWN_OVER,
        price,
        "10(f)",
        (
            f"NREAC bottomed at ${state.nreac_trough:.2f}, just ${gap:.1f} above "
            f"DT pivot ${dt_piv.price:.2f}, then rallied ${rise:.1f} — downtrend may be over"
        ),
        pivot_ref=dt_piv,
        dedup_override=f"NREAC_trough_{state.nreac_trough}",
    )

"""One-call chart constructors that compose styles, panes, and layout."""

from __future__ import annotations

from collections.abc import Sequence

from lafmm.chart.layout import Chart, HLine, Pane, render_chart
from lafmm.chart.styles import (
    CandleSeries,
    HistogramSeries,
    LineSeries,
)
from lafmm.indicators import (
    adx,
    bollinger,
    cci,
    dema,
    ema,
    macd,
    obv,
    relative_volume,
    rma,
    rsi,
    sma,
    stochastic,
    tema,
    vwap,
    williams_r,
)


def line_chart(
    values: Sequence[float],
    *,
    width: int = 80,
    height: int = 20,
    color: str = "green",
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    return render_chart(
        Chart(
            panes=(Pane(series=(LineSeries(ys=tuple(values), color=color),)),),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def candlestick_chart(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    width: int = 80,
    height: int = 20,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(
                        CandleSeries(
                            opens=tuple(opens),
                            highs=tuple(highs),
                            lows=tuple(lows),
                            closes=tuple(closes),
                        ),
                    )
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def macd_chart(
    closes: Sequence[float],
    *,
    width: int = 80,
    height: int = 30,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    ml, sl, hist = macd(closes, fast, slow, signal)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(
                        HistogramSeries(ys=tuple(hist), dual_color=True, label="Hist"),
                        LineSeries(ys=tuple(ml), color="cyan", label="MACD"),
                        LineSeries(ys=tuple(sl), color="yellow", label="Signal"),
                    ),
                    height_weight=1,
                    hlines=(HLine(0.0, label="Zero"),),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def rsi_chart(
    closes: Sequence[float],
    *,
    width: int = 80,
    height: int = 24,
    period: int = 14,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    rsi_vals = rsi(closes, period)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(LineSeries(ys=tuple(rsi_vals), color="magenta", label="RSI"),),
                    height_weight=1,
                    y_range=(0.0, 100.0),
                    hlines=(HLine(70.0, "red", label="OB 70"), HLine(30.0, "green", label="OS 30")),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def overlay_chart(
    closes: Sequence[float],
    *,
    overlays: Sequence[tuple[str, int]] = (),
    width: int = 80,
    height: int = 20,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    colors = ("yellow", "cyan", "magenta", "bright_green", "bright_red")
    series_list: list[LineSeries] = [LineSeries(ys=tuple(closes), color="white", label="Close")]
    ma_fns = {"sma": sma, "ema": ema, "rma": rma, "dema": dema, "tema": tema}
    for idx, (kind, period) in enumerate(overlays):
        fn = ma_fns.get(kind.lower(), ema)
        vals = fn(closes, period)
        tag = f"{kind.upper()}({period})"
        series_list.append(LineSeries(ys=tuple(vals), color=colors[idx % len(colors)], label=tag))
    return render_chart(
        Chart(
            panes=(Pane(series=tuple(series_list)),),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def bollinger_chart(
    closes: Sequence[float],
    *,
    period: int = 20,
    band_width: float = 2.0,
    width: int = 80,
    height: int = 20,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    mid, upper, lower = bollinger(closes, period, band_width)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(
                        LineSeries(ys=tuple(closes), color="white", label="Close"),
                        LineSeries(ys=tuple(mid), color="yellow", label=f"SMA({period})"),
                        LineSeries(ys=tuple(upper), color="cyan", label="Upper"),
                        LineSeries(ys=tuple(lower), color="cyan", label="Lower"),
                    ),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def stochastic_chart(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    k_period: int = 14,
    d_period: int = 3,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    k_line, d_line = stochastic(highs, lows, closes, k_period, d_period)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(
                        LineSeries(ys=tuple(k_line), color="cyan", label=f"%K({k_period})"),
                        LineSeries(ys=tuple(d_line), color="yellow", label=f"%D({d_period})"),
                    ),
                    height_weight=1,
                    y_range=(0.0, 100.0),
                    hlines=(HLine(80.0, "red", label="OB 80"), HLine(20.0, "green", label="OS 20")),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def adx_chart(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    period: int = 14,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    adx_vals = adx(highs, lows, closes, period)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(
                        LineSeries(ys=tuple(adx_vals), color="yellow", label=f"ADX({period})"),
                    ),
                    height_weight=1,
                    hlines=(HLine(25.0, "gray", label="Trend 25"),),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def williams_r_chart(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    period: int = 14,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    wr_vals = williams_r(highs, lows, closes, period)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(LineSeries(ys=tuple(wr_vals), color="cyan", label=f"%R({period})"),),
                    height_weight=1,
                    y_range=(-100.0, 0.0),
                    hlines=(
                        HLine(-20.0, "red", label="OB -20"),
                        HLine(-80.0, "green", label="OS -80"),
                    ),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def cci_chart(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    period: int = 20,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    cci_vals = cci(highs, lows, closes, period)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(
                        LineSeries(ys=tuple(cci_vals), color="yellow", label=f"CCI({period})"),
                    ),
                    height_weight=1,
                    hlines=(
                        HLine(100.0, "red", label="OB +100"),
                        HLine(-100.0, "green", label="OS -100"),
                        HLine(0.0),
                    ),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def obv_chart(
    closes: Sequence[float],
    volumes: Sequence[float],
    *,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    obv_vals = obv(closes, volumes)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(LineSeries(ys=tuple(obv_vals), color="cyan", label="OBV"),),
                    height_weight=1,
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def vwap_chart(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    *,
    width: int = 80,
    height: int = 20,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    vwap_vals = vwap(highs, lows, closes, volumes)
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(
                        LineSeries(ys=tuple(closes), color="white", label="Close"),
                        LineSeries(ys=tuple(vwap_vals), color="yellow", label="VWAP"),
                    ),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def volume_chart(
    closes: Sequence[float],
    volumes: Sequence[float],
    *,
    period: int = 20,
    width: int = 80,
    height: int = 24,
    title: str = "",
    x_labels: Sequence[str] = (),
) -> str:
    bar_colors = _volume_colors(closes)
    rvol = relative_volume(volumes, period)
    cap = max(volumes) * 1.05 if volumes else 1.0
    return render_chart(
        Chart(
            panes=(
                Pane(
                    series=(LineSeries(ys=tuple(closes), color="white", label="Close"),),
                    height_weight=3,
                ),
                Pane(
                    series=(
                        HistogramSeries(
                            ys=tuple(volumes), colors=bar_colors,
                            dual_color=True, label="Vol",
                        ),
                    ),
                    y_range=(0.0, cap),
                    height_weight=1,
                ),
                Pane(
                    series=(LineSeries(ys=tuple(rvol), color="yellow", label=f"RVOL({period})"),),
                    height_weight=0.5,
                    hlines=(HLine(1.0, "gray", label="Avg"),),
                ),
            ),
            width=width,
            height=height,
            title=title,
            x_labels=tuple(x_labels),
        )
    )


def _volume_colors(closes: Sequence[float]) -> tuple[str, ...]:
    return tuple(
        "green" if i == 0 or closes[i] >= closes[i - 1] else "red"
        for i in range(len(closes))
    )

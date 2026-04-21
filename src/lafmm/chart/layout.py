"""Pane layout and chart orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from lafmm.chart.canvas import Canvas
from lafmm.chart.styles import (
    AnySeries,
    AreaSeries,
    CandleSeries,
    HistogramSeries,
    LineSeries,
    Viewport,
    _candle_width,
    draw_series,
)


@dataclass(frozen=True)
class HLine:
    value: float
    color: str = "gray"
    char: str = "╌"
    label: str = ""


@dataclass(frozen=True)
class Pane:
    series: tuple[AnySeries, ...]
    height_weight: float = 1.0
    y_range: tuple[float, float] | None = None
    hlines: tuple[HLine, ...] = ()


@dataclass(frozen=True)
class Chart:
    panes: tuple[Pane, ...]
    width: int = 80
    height: int = 24
    title: str = ""
    x_labels: tuple[str, ...] = ()


def render_chart(chart: Chart) -> str:
    canvas = Canvas(chart.width, chart.height)
    label_w = _label_width(chart)
    draw_left = label_w + 2
    draw_w = max(1, chart.width - draw_left - 1)
    has_legend = _has_labels(chart)
    heights = _pane_heights(chart)

    y = 0
    if chart.title:
        canvas.text(1, 0, chart.title, "white")
        y = 1
    if has_legend:
        _draw_legend(canvas, chart, draw_left, y)
        y += 1

    for pane, h in zip(chart.panes, heights, strict=True):
        _render_pane(canvas, pane, draw_left, y, draw_w, h, label_w)
        y += h

    if chart.x_labels:
        _draw_x_axis(canvas, draw_left, y, draw_w, chart.x_labels)

    return canvas.render()


# ── Pane rendering ───────────────────────────────────────────────────


def _render_pane(
    canvas: Canvas,
    pane: Pane,
    left: int,
    top: int,
    width: int,
    height: int,
    label_w: int,
) -> None:
    y_lo, y_hi = _y_range(pane)
    n = _data_len(pane)
    pad = _candle_pad(pane, width, n)
    vp = Viewport(0, max(1, n - 1), y_lo, y_hi, left + pad, top, width - pad * 2, height)

    _draw_y_axis(canvas, vp, left - 1, label_w)
    for hl in pane.hlines:
        _draw_hline(canvas, vp, hl)
    for s in pane.series:
        draw_series(canvas, vp, s)


def _candle_pad(pane: Pane, width: int, n: int) -> int:
    for s in pane.series:
        if isinstance(s, CandleSeries):
            return _candle_width(width, n) // 2
    return 0


# ── Y-range auto-detection ──────────────────────────────────────────


def _y_range(pane: Pane) -> tuple[float, float]:
    if pane.y_range is not None:
        return pane.y_range
    vals: list[float] = []
    for s in pane.series:
        _collect_y_values(s, vals)
    if not vals:
        return (0.0, 1.0)
    lo, hi = min(vals), max(vals)
    margin = max((hi - lo) * 0.1, (hi - lo) * 0.05 + abs(hi + lo) * 0.02, 0.5)
    return (lo - margin, hi + margin)


def _collect_y_values(s: AnySeries, vals: list[float]) -> None:
    match s:
        case LineSeries(ys=ys) | AreaSeries(ys=ys):
            vals.extend(ys)
        case HistogramSeries(ys=ys, baseline=b):
            vals.extend(ys)
            vals.append(b)
        case CandleSeries(highs=h, lows=l):
            vals.extend(h)
            vals.extend(l)


def _data_len(pane: Pane) -> int:
    for s in pane.series:
        match s:
            case LineSeries(ys=ys) | AreaSeries(ys=ys) | HistogramSeries(ys=ys):
                return len(ys)
            case CandleSeries(closes=c):
                return len(c)
    return 0


# ── Height allocation ────────────────────────────────────────────────


def _pane_heights(chart: Chart) -> list[int]:
    title_h = 1 if chart.title else 0
    legend_h = 1 if _has_labels(chart) else 0
    x_axis_h = 1 if chart.x_labels else 0
    avail = max(len(chart.panes) * 3, chart.height - title_h - legend_h - x_axis_h)
    total_w = sum(p.height_weight for p in chart.panes)
    heights = [max(3, round(p.height_weight / total_w * avail)) for p in chart.panes]
    heights[0] += avail - sum(heights)
    return heights


def _label_width(chart: Chart) -> int:
    max_w = 0
    for pane in chart.panes:
        lo, hi = _y_range(pane)
        max_w = max(max_w, len(_fmt(lo)), len(_fmt(hi)))
    return max(max_w, 4)


# ── Legend ────────────────────────────────────────────────────────────


def _has_labels(chart: Chart) -> bool:
    return any(s.label for p in chart.panes for s in p.series) or any(
        hl.label for p in chart.panes for hl in p.hlines
    )


def _series_color(s: AnySeries) -> str:
    match s:
        case LineSeries(color=c) | AreaSeries(color=c) | HistogramSeries(color=c):
            return c
        case CandleSeries():
            return s.up_color


def _draw_legend(canvas: Canvas, chart: Chart, left: int, y: int) -> None:
    x = left
    for pane in chart.panes:
        for s in pane.series:
            if not s.label:
                continue
            x = _draw_legend_entry(canvas, x, y, s)
        for hl in pane.hlines:
            if not hl.label:
                continue
            canvas.text(x, y, hl.char * 2, hl.color)
            canvas.text(x + 3, y, hl.label, "gray")
            x += len(hl.label) + 6


def _draw_legend_entry(canvas: Canvas, x: int, y: int, s: AnySeries) -> int:
    match s:
        case HistogramSeries(dual_color=True):
            canvas.text(x, y, "█", s.up_color)
            canvas.text(x + 1, y, "█", s.down_color)
        case _:
            canvas.text(x, y, "━━", _series_color(s))
    canvas.text(x + 3, y, s.label, "gray")
    return x + len(s.label) + 6


# ── Axis drawing ─────────────────────────────────────────────────────


def _draw_y_axis(canvas: Canvas, vp: Viewport, axis_x: int, label_w: int) -> None:
    canvas.vline(axis_x, vp.top, vp.top + vp.height - 1, "│", "gray")
    ticks = min(5, vp.height // 3)
    if ticks == 0:
        return
    for i in range(ticks + 1):
        y = vp.top + round(i * (vp.height - 1) / ticks)
        val = vp.y_max - (vp.y_max - vp.y_min) * i / ticks
        label = _fmt(val).rjust(label_w)
        canvas.text(axis_x - label_w, y, label, "gray")
        canvas.text(axis_x, y, "┤", "gray")


def _draw_hline(canvas: Canvas, vp: Viewport, hl: HLine) -> None:
    y = round(vp.map_y(hl.value))
    if vp.top <= y < vp.top + vp.height:
        canvas.hline(y, vp.left, vp.left + vp.width - 1, hl.char, hl.color, soft=True)


def _draw_x_axis(
    canvas: Canvas,
    left: int,
    y: int,
    width: int,
    labels: tuple[str, ...],
) -> None:
    if y >= canvas.height or not labels:
        return
    n = len(labels)
    max_label_w = max(len(lb) for lb in labels)
    max_labels = max(1, width // (max_label_w + 2))
    step = max(1, (n - 1) // max_labels) if n > 1 else 1
    next_free = left
    for i in range(0, n, step):
        data_x = left + round(i / max(1, n - 1) * (width - 1)) if n > 1 else left
        cx = max(next_free, data_x - len(labels[i]) // 2)
        if cx + len(labels[i]) > left + width:
            break
        canvas.text(cx, y, labels[i], "gray")
        next_free = cx + len(labels[i]) + 1


def _fmt(v: float) -> str:
    a = abs(v)
    if a >= 10000:
        return f"{v:,.0f}"
    if a >= 100:
        return f"{v:.0f}"
    if a >= 10:
        return f"{v:.1f}"
    if a >= 0.01:
        return f"{v:.2f}"
    return f"{v:.3f}"

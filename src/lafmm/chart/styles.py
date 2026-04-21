"""Series types and style renderers."""

from __future__ import annotations

from dataclasses import dataclass

from lafmm.chart.canvas import Canvas


@dataclass(frozen=True)
class Viewport:
    """Maps data coordinates to canvas positions."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    left: int
    top: int
    width: int
    height: int

    def map_x(self, x: float) -> float:
        if self.x_max == self.x_min:
            return self.left + self.width / 2
        return self.left + (x - self.x_min) / (self.x_max - self.x_min) * (self.width - 1)

    def map_y(self, y: float) -> float:
        if self.y_max == self.y_min:
            return self.top + self.height / 2
        return (
            self.top
            + self.height
            - 1
            - (y - self.y_min) / (self.y_max - self.y_min) * (self.height - 1)
        )


# ── Series types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class LineSeries:
    ys: tuple[float, ...]
    color: str = "green"
    label: str = ""


@dataclass(frozen=True)
class CandleSeries:
    opens: tuple[float, ...]
    highs: tuple[float, ...]
    lows: tuple[float, ...]
    closes: tuple[float, ...]
    up_color: str = "green"
    down_color: str = "red"
    label: str = ""


@dataclass(frozen=True)
class HistogramSeries:
    ys: tuple[float, ...]
    color: str = "cyan"
    up_color: str = "green"
    down_color: str = "red"
    baseline: float = 0.0
    dual_color: bool = False
    label: str = ""
    colors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AreaSeries:
    ys: tuple[float, ...]
    color: str = "green"
    label: str = ""


type AnySeries = LineSeries | CandleSeries | HistogramSeries | AreaSeries


# ── Draw dispatch ────────────────────────────────────────────────────


def draw_series(canvas: Canvas, vp: Viewport, series: AnySeries) -> None:
    match series:
        case LineSeries():
            _draw_line(canvas, vp, series)
        case CandleSeries():
            _draw_candles(canvas, vp, series)
        case HistogramSeries():
            _draw_histogram(canvas, vp, series)
        case AreaSeries():
            _draw_area(canvas, vp, series)


# ── Style renderers ──────────────────────────────────────────────────


def _draw_line(canvas: Canvas, vp: Viewport, s: LineSeries) -> None:
    if len(s.ys) == 1:
        canvas.dot(round(vp.map_x(0) * 2), round(vp.map_y(s.ys[0]) * 4), s.color)
        return
    for i in range(len(s.ys) - 1):
        canvas.line(
            vp.map_x(i),
            vp.map_y(s.ys[i]),
            vp.map_x(i + 1),
            vp.map_y(s.ys[i + 1]),
            s.color,
        )


def _draw_candles(canvas: Canvas, vp: Viewport, s: CandleSeries) -> None:
    n = len(s.closes)
    if n == 0:
        return
    bw = _candle_width(vp.width, n)
    for i in range(n):
        color = s.up_color if s.closes[i] >= s.opens[i] else s.down_color
        _draw_one_candle(canvas, vp, i, s.opens[i], s.highs[i], s.lows[i], s.closes[i], color, bw)


def _candle_width(draw_w: int, n: int) -> int:
    spacing = draw_w / max(1, n)
    if spacing >= 7:
        return 5
    if spacing >= 4:
        return 3
    return 1


def _draw_one_candle(
    canvas: Canvas,
    vp: Viewport,
    i: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    color: str,
    bw: int,
) -> None:
    cx = round(vp.map_x(i))
    yh, yl = round(vp.map_y(high)), round(vp.map_y(low))
    yo, yc = round(vp.map_y(open_)), round(vp.map_y(close))
    bt, bb = min(yo, yc), max(yo, yc)
    body_left = cx - bw // 2

    if yh < bt:
        canvas.vline(cx, yh, bt - 1, "│", color)
    if bb < yl:
        canvas.vline(cx, bb + 1, yl, "│", color)
    canvas.rect(body_left, bt, bw, max(1, bb - bt + 1), "█", color)


def _draw_histogram(canvas: Canvas, vp: Viewport, s: HistogramSeries) -> None:
    base_y = round(vp.map_y(s.baseline))
    n = len(s.ys)
    if n == 0:
        return
    num_bars = min(n, (vp.width + 1) // 2)
    for b in range(num_bars):
        cx = vp.left + b * 2
        i = round(b / max(1, num_bars - 1) * (n - 1)) if num_bars > 1 else 0
        val = s.ys[i]
        vy = round(vp.map_y(val))
        if vy == base_y:
            continue
        if s.colors:
            color = s.colors[i]
        elif s.dual_color:
            color = s.up_color if val >= s.baseline else s.down_color
        else:
            color = s.color
        top, bot = min(vy, base_y), max(vy, base_y)
        canvas.rect(cx, top, 1, bot - top + 1, "▒", color, soft=True)


def _draw_area(canvas: Canvas, vp: Viewport, s: AreaSeries) -> None:
    n = len(s.ys)
    if n == 0:
        return
    bottom = vp.top + vp.height - 1
    x_first, x_last = round(vp.map_x(0)), round(vp.map_x(n - 1))
    for cx in range(x_first, x_last + 1):
        cy = round(vp.map_y(_lerp_y(s.ys, cx, vp)))
        if cy <= bottom:
            canvas.rect(cx, cy, 1, bottom - cy + 1, "█", s.color)


def _lerp_y(ys: tuple[float, ...], cx: int, vp: Viewport) -> float:
    n = len(ys)
    if n == 1:
        return ys[0]
    data_x = (cx - vp.left) / max(1, vp.width - 1) * (vp.x_max - vp.x_min) + vp.x_min
    i = max(0, min(int(data_x), n - 2))
    t = max(0.0, min(1.0, data_x - i))
    return ys[i] + (ys[min(i + 1, n - 1)] - ys[i]) * t

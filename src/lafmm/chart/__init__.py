"""Chart rendering: bars, sparklines, and canvas-based charts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lafmm.chart.bars import horizontal_bars, sparkline, vertical_bars
from lafmm.chart.canvas import Canvas
from lafmm.chart.composers import (
    adx_chart,
    bollinger_chart,
    candlestick_chart,
    cci_chart,
    line_chart,
    macd_chart,
    obv_chart,
    overlay_chart,
    rsi_chart,
    stochastic_chart,
    volume_chart,
    vwap_chart,
    williams_r_chart,
)
from lafmm.chart.layout import Chart, HLine, Pane, render_chart
from lafmm.chart.styles import (
    AnySeries,
    AreaSeries,
    CandleSeries,
    HistogramSeries,
    LineSeries,
    Viewport,
)

if TYPE_CHECKING:
    from rich.text import Text

__all__ = [
    "AnySeries",
    "AreaSeries",
    "CandleSeries",
    "Canvas",
    "Chart",
    "HLine",
    "HistogramSeries",
    "LineSeries",
    "Pane",
    "Viewport",
    "adx_chart",
    "bollinger_chart",
    "candlestick_chart",
    "cci_chart",
    "chart_to_text",
    "horizontal_bars",
    "line_chart",
    "macd_chart",
    "obv_chart",
    "overlay_chart",
    "render_chart",
    "rsi_chart",
    "sparkline",
    "stochastic_chart",
    "vertical_bars",
    "volume_chart",
    "vwap_chart",
    "williams_r_chart",
]


def chart_to_text(ansi_str: str) -> Text:
    """Bridge ANSI chart output to Rich Text for TUI integration."""
    from rich.text import Text

    return Text.from_ansi(ansi_str)

"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

# ──────────────────────── LAFMM Theme ────────────────────────────
#
# | Role              | Hex       | Usage                              |
# |-------------------|-----------|------------------------------------|
# | BG                | #1a1b26   | Screen background                  |
# | BG_DEEP           | #16161e   | App header/footer chrome           |
# | BG_ELEVATED       | #24283b   | Header bars, key highlights        |
# | BG_SUBTLE         | #1e1e2e   | Odd table rows                     |
# | BG_HOVER          | #1e2030   | Row hover                          |
# | BG_CURSOR         | #1a2a3a   | Selected row                       |
# | FG                | #c0caf5   | Primary text                       |
# | FG_DIM            | #a9b1d6   | Header text                        |
# | FG_MUTED          | #565f89   | Labels, column headers, chrome     |
# | FG_ACCENT         | #7aa2f7   | Key highlights in footer           |
# | FG_FAINT          | #3b4261   | Scrollbar                          |
# | POSITIVE          | #4ed47e   | BUY, uptrend, bullish              |
# | NEGATIVE          | #e46565   | SELL, downtrend, bearish           |
# | NEUTRAL           | #dbd285   | Neutral trend, warnings            |
# | WATCH             | #4db9e4   | Approaching pivot                  |
# | DANGER            | #e4964d   | Trend may be ending                |
# | KEY_GRAD_START    | rgb(220,180,120) | KEY signal row gradient start |
# | KEY_GRAD_END      | rgb(180,120,100) | KEY signal row gradient end   |

BG = "#1a1b26"
BG_DEEP = "#16161e"
BG_ELEVATED = "#24283b"
BG_SUBTLE = "#1e1e2e"
BG_HOVER = "#1e2030"
BG_CURSOR = "#1a2a3a"

FG = "#c0caf5"
FG_DIM = "#a9b1d6"
FG_MUTED = "#565f89"
FG_ACCENT = "#7aa2f7"
FG_FAINT = "#3b4261"

POSITIVE = "#4ed47e"
NEGATIVE = "#e46565"
NEUTRAL = "#dbd285"
WATCH = "#4db9e4"
DANGER = "#e4964d"

KEY_GRAD_START = (220, 180, 120)
KEY_GRAD_END = (180, 120, 100)

# ── Terminal Palette (Rich console — stats, charts) ─────────────────
#
# Raw terminal colors for standalone Rich output. Punchier than the
# TUI theme — sparse dashboards need contrast, dense TUI tables don't.

TERM_POSITIVE = "green"
TERM_NEGATIVE = "red"
TERM_NEUTRAL = "yellow"
TERM_WATCH = "cyan"

ROTATION_ANSI: tuple[str, ...] = (
    "cyan",
    "magenta",
    "yellow",
    "green",
    "blue",
    "red",
    "white",
    "gray",
)

ROTATION_RICH: tuple[str, ...] = (
    "cyan",
    "magenta",
    "yellow",
    "green",
    "blue",
    "red",
    "white",
    "orange1",
    "purple",
    "turquoise2",
    "hot_pink",
    "chartreuse1",
    "deep_sky_blue1",
    "gold1",
    "orchid",
    "spring_green1",
)

ANSI: dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def color_by_threshold(value: float, good: float, neutral: float) -> str:
    if value >= good:
        return TERM_POSITIVE
    return TERM_NEUTRAL if value >= neutral else TERM_NEGATIVE

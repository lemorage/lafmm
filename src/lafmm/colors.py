"""SPDX-License-Identifier: GPL-3.0-only"""

from __future__ import annotations

POSITIVE = "green"
NEGATIVE = "red"
NEUTRAL = "yellow"

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
        return POSITIVE
    return NEUTRAL if value >= neutral else NEGATIVE

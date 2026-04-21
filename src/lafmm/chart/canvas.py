"""Character grid with ANSI color and braille sub-pixel rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

# Braille dot bits indexed by row * 2 + col (row 0-3, col 0-1)
_DOT_BITS = (0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80)

_COLORS: dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_cyan": "\033[96m",
}

_RESET = "\033[0m"


@dataclass
class Canvas:
    """Mutable character grid with braille sub-pixel line drawing."""

    width: int
    height: int
    _cells: list[str] = field(init=False, repr=False)
    _colors: list[str] = field(init=False, repr=False)
    _soft: list[bool] = field(init=False, repr=False)
    _dots: list[int] = field(init=False, repr=False)
    _dot_colors: list[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        n = self.width * self.height
        self._cells = [" "] * n
        self._colors = [""] * n
        self._soft = [False] * n
        self._dots = [0] * n
        self._dot_colors = [""] * n

    def _idx(self, x: int, y: int) -> int | None:
        if 0 <= x < self.width and 0 <= y < self.height:
            return y * self.width + x
        return None

    def text(self, x: int, y: int, s: str, color: str = "") -> None:
        for i, ch in enumerate(s):
            if (idx := self._idx(x + i, y)) is not None:
                self._cells[idx] = ch
                self._colors[idx] = color

    def hline(
        self,
        y: int,
        x0: int,
        x1: int,
        char: str = "─",
        color: str = "",
        *,
        soft: bool = False,
    ) -> None:
        for x in range(max(0, x0), min(self.width, x1 + 1)):
            if (idx := self._idx(x, y)) is not None:
                self._cells[idx] = char
                self._colors[idx] = color
                self._soft[idx] = soft

    def vline(self, x: int, y0: int, y1: int, char: str = "│", color: str = "") -> None:
        for y in range(max(0, y0), min(self.height, y1 + 1)):
            if (idx := self._idx(x, y)) is not None:
                self._cells[idx] = char
                self._colors[idx] = color

    def rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        char: str = "█",
        color: str = "",
        *,
        soft: bool = False,
    ) -> None:
        for dy in range(h):
            for dx in range(w):
                if (idx := self._idx(x + dx, y + dy)) is not None:
                    self._cells[idx] = char
                    self._colors[idx] = color
                    self._soft[idx] = soft

    def fill(self, x: int, y: int, w: int, h: int, char: str, color: str = "") -> None:
        self.rect(x, y, w, h, char, color)

    def dot(self, sx: int, sy: int, color: str = "") -> None:
        """Set a braille dot at sub-pixel coords (2 cols x 4 rows per cell)."""
        cx, cy = sx // 2, sy // 4
        if (idx := self._idx(cx, cy)) is None:
            return
        self._dots[idx] |= _DOT_BITS[(sy % 4) * 2 + (sx % 2)]
        if color:
            self._dot_colors[idx] = color

    def line(self, x0: float, y0: float, x1: float, y1: float, color: str = "") -> None:
        """Braille line between two points in character-cell coordinates."""
        _bresenham(self, round(x0 * 2), round(y0 * 4), round(x1 * 2), round(y1 * 4), color)

    def render(self) -> str:
        return "\n".join(_render_row(self, y) for y in range(self.height))


def _bresenham(canvas: Canvas, x0: int, y0: int, x1: int, y1: int, color: str) -> None:
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        canvas.dot(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _render_row(canvas: Canvas, y: int) -> str:
    parts: list[str] = []
    prev_ansi = ""

    for x in range(canvas.width):
        idx = y * canvas.width + x
        char, color = canvas._cells[idx], canvas._colors[idx]

        if canvas._dots[idx] and (char == " " or canvas._soft[idx]):
            char = chr(0x2800 | canvas._dots[idx])
            color = canvas._dot_colors[idx]

        ansi = _COLORS.get(color, "")
        if ansi != prev_ansi:
            if prev_ansi:
                parts.append(_RESET)
            if ansi:
                parts.append(ansi)
            prev_ansi = ansi
        parts.append(char)

    if prev_ansi:
        parts.append(_RESET)
    return "".join(parts)

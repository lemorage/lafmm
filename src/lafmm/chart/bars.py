"""Terminal charts — sparklines and bar charts with Rich markup."""

from __future__ import annotations

from collections.abc import Sequence

BLOCKS = " ▁▂▃▄▅▆▇█"


def sparkline(values: Sequence[float], color: str = "green") -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    spread = hi - lo or 1.0
    chars = [BLOCKS[max(1, min(8, round((v - lo) / spread * 8)))] for v in values]
    return f"[{color}]{''.join(chars)}[/]"


def vertical_bars(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    height: int = 10,
    bar_width: int = 3,
    gap: int = 1,
) -> str:
    if not values:
        return ""
    max_p = max((v for v in values if v > 0), default=0.0)
    max_n = abs(min((v for v in values if v < 0), default=0.0))
    if max_p == 0 and max_n == 0:
        return ""

    pos_h, neg_h = _split_height(max_p, max_n, height)
    y_w = max(len(_compact(max_p)), len(_compact(-max_n)), 2) + 1
    lines: list[str] = []

    _render_value_labels(lines, values, bar_width + gap, y_w)
    _render_positive_region(lines, values, max_p, pos_h, bar_width, gap, y_w)
    _render_zero_line(lines, len(values), bar_width + gap, y_w)
    _render_negative_region(lines, values, max_n, neg_h, bar_width, gap, y_w)
    _render_x_labels(lines, labels, bar_width + gap, y_w)

    return "\n".join(lines)


def horizontal_bars(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int = 30,
) -> str:
    if not values:
        return ""
    max_abs = max(abs(v) for v in values) or 1.0
    label_w = max(len(lb) for lb in labels)
    val_nums = [_pnl_num(v) for v in values]
    val_w = max(len(s) for s in val_nums)

    lines: list[str] = []
    for label, value, num in zip(labels, values, val_nums, strict=True):
        bar_len = max(1, round(abs(value) / max_abs * width))
        color = "green" if value >= 0 else "red"
        bar = f"[{color}]{'█' * bar_len}[/]"
        pad = " " * (width - bar_len)
        colored = f"[{color}]{num.rjust(val_w)}[/]"
        lines.append(f"  {label.ljust(label_w)}  {bar}{pad}  {colored}")
    return "\n".join(lines)


# ── Internals ───────────────────────────────────────────────────────


def _split_height(max_p: float, max_n: float, height: int) -> tuple[int, int]:
    if max_p > 0 and max_n > 0:
        ratio = max_p / (max_p + max_n)
        p = max(2, round(ratio * height))
        return p, max(2, height - p)
    return (height, 0) if max_p > 0 else (0, height)


def _render_positive_region(
    lines: list[str],
    values: Sequence[float],
    max_p: float,
    pos_h: int,
    bw: int,
    gap: int,
    y_w: int,
) -> None:
    for r in range(pos_h - 1, -1, -1):
        y = _compact(max_p).rjust(y_w) if r == pos_h - 1 else " " * y_w
        row = _pos_row(values, max_p, pos_h, r, bw, gap)
        lines.append(f"{y} ┤{row}")


def _render_negative_region(
    lines: list[str],
    values: Sequence[float],
    max_n: float,
    neg_h: int,
    bw: int,
    gap: int,
    y_w: int,
) -> None:
    for r in range(neg_h):
        y = _compact(-max_n).rjust(y_w) if r == neg_h - 1 else " " * y_w
        row = _neg_row(values, max_n, neg_h, r, bw, gap)
        lines.append(f"{y} │{row}")


def _render_zero_line(
    lines: list[str],
    n_bars: int,
    col_w: int,
    y_w: int,
) -> None:
    lines.append(f"{'0'.rjust(y_w)} ┼{'─' * (n_bars * col_w)}")


def _render_x_labels(
    lines: list[str],
    labels: Sequence[str],
    col_w: int,
    y_w: int,
) -> None:
    x_line = "".join(lb.center(col_w) for lb in labels)
    lines.append(f"{' ' * (y_w + 2)}{x_line}")


def _render_value_labels(
    lines: list[str],
    values: Sequence[float],
    col_w: int,
    y_w: int,
) -> None:
    bar_w = col_w - 1
    gap = 1
    parts: list[str] = []
    for val in values:
        color = "green" if val >= 0 else "red"
        label = _compact_precise(val)
        parts.append(f"[{color}]{label.center(bar_w)}[/]{' ' * gap}")
    lines.append(f"{' ' * (y_w + 2)}{''.join(parts)}")


def _compact_precise(v: float) -> str:
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 10_000:
        return f"{sign}${a / 1000:.2f}k"
    if a >= 1000:
        return f"{sign}${a / 1000:.2f}k"
    return f"{sign}${a:,.0f}"


def _pos_row(
    values: Sequence[float],
    max_p: float,
    rows: int,
    row: int,
    bw: int,
    gap: int,
) -> str:
    parts: list[str] = []
    for v in values:
        eighths = (v / max_p * rows - row) * 8 if v > 0 else 0
        parts.append(_up_fill(eighths, bw, "green") + " " * gap)
    return "".join(parts)


def _neg_row(
    values: Sequence[float],
    max_n: float,
    rows: int,
    row: int,
    bw: int,
    gap: int,
) -> str:
    parts: list[str] = []
    for v in values:
        eighths = (abs(v) / max_n * rows - row) * 8 if v < 0 else 0
        parts.append(_down_fill(eighths, bw, "red") + " " * gap)
    return "".join(parts)


def _up_fill(eighths: float, width: int, color: str) -> str:
    n = max(0, min(8, round(eighths)))
    if n == 0:
        return " " * width
    return f"[{color}]{BLOCKS[n] * width}[/]"


def _down_fill(eighths: float, width: int, color: str) -> str:
    n = max(0, min(8, round(eighths)))
    if n == 0:
        return " " * width
    if n == 8:
        return f"[{color}]{'█' * width}[/]"
    return f"[black on {color}]{BLOCKS[8 - n] * width}[/]"


def _compact(v: float) -> str:
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 10_000:
        return f"{sign}${a / 1000:.0f}k"
    if a >= 1000:
        return f"{sign}${a / 1000:.1f}k"
    return f"{sign}${a:,.0f}"


def _pnl_num(v: float) -> str:
    if v >= 0:
        return f"+${v:,.2f}"
    return f"-${abs(v):,.2f}"

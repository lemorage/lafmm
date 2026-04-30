"""Thought tape: capture trading observations at the moment of decision."""

from __future__ import annotations

import re
from datetime import date as dt
from datetime import timedelta
from pathlib import Path

from rich.console import Console


def tape_path(root: Path) -> Path:
    return root / "tape.md"


def _splice_entry(existing: str, header: str, new_content: str) -> str:
    if f"\n{header}\n" not in f"\n{existing}\n":
        entry = f"{header}\n\n{new_content}\n"
        return existing.rstrip() + "\n\n" + entry if existing.strip() else entry
    pos = existing.index(header)
    next_header = existing.find("\n## ", pos + len(header))
    if next_header == -1:
        return existing.rstrip() + "\n" + new_content + "\n"
    return existing[:next_header].rstrip() + "\n" + new_content + "\n" + existing[next_header:]


def save_thought(root: Path, trade_date: str, text: str) -> int:
    content = text.strip()
    if not content:
        return 0
    path = tape_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.exists() else ""
    path.write_text(_splice_entry(existing, f"## {trade_date}", content))
    return len([line for line in content.splitlines() if line.strip()])


def read_interactive(con: Console, trade_date: str) -> str:
    con.print()
    con.print(f"  [bold]◆[/] [cyan]{trade_date}[/]  [dim](ctrl+d to save)[/]")
    con.print("  [dim]│[/]")
    lines: list[str] = []
    try:
        while True:
            raw = input("  │  ")
            lines.append(raw)
    except EOFError:
        pass
    con.print("  [dim]└[/]")
    return "\n".join(lines)


def _parse_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for chunk in text.split("\n## "):
        chunk = chunk.strip()
        if not chunk:
            continue
        clean = chunk.removeprefix("## ")
        header, _, body = clean.partition("\n")
        if header.strip():
            entries.append((header.strip(), body.strip()))
    return entries


def show_queue(root: Path, con: Console) -> None:
    path = tape_path(root)
    text = path.read_text() if path.exists() else ""
    entries = _parse_entries(text) if text.strip() else []
    if not entries:
        con.print()
        con.print("  [dim]no pending tapes[/]")
        con.print()
        con.print('  lafmm tape [cyan]<when>[/] "bought NVDA at support"')
        con.print("  lafmm tape [cyan]<when>[/]                           [dim]← interactive[/]")
        con.print()
        con.print("  [dim]when:[/] today · yesterday · 3d · 04-25")
        return
    con.print()
    for header, body in entries:
        body_lines = [line for line in body.splitlines() if line.strip()]
        con.print(f"  [bold]◆[/] [cyan]{header}[/] [dim]· {len(body_lines)} lines[/]")
        for line in body_lines[:3]:
            con.print(f"  [dim]│[/]  {line}")
        if len(body_lines) > 3:
            con.print("  [dim]│[/]  [dim]...[/]")
        con.print()
    con.print(f"  [dim]{len(entries)} pending · agent will pick these up during trade sync[/]")


def _parse_date(raw: str) -> str | None:
    shortcuts = {"today": 0, "yesterday": 1}
    if raw.lower() in shortcuts:
        return (dt.today() - timedelta(days=shortcuts[raw.lower()])).isoformat()
    if re.match(r"^\d{1,3}d$", raw):
        return (dt.today() - timedelta(days=int(raw[:-1]))).isoformat()
    if re.match(r"^\d{1,3}$", raw):
        return (dt.today() - timedelta(days=int(raw))).isoformat()
    candidate = None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        candidate = raw
    elif re.match(r"^\d{2}-\d{2}$", raw):
        candidate = f"{dt.today().year}-{raw}"
    if candidate:
        try:
            dt.fromisoformat(candidate)
            return candidate
        except ValueError:
            return None
    return None


def run_tape(root: Path, trade_date: str | None, text: str | None) -> None:
    con = Console()
    if trade_date is None:
        show_queue(root, con)
        return
    parsed = _parse_date(trade_date)
    if parsed is None:
        con.print(f"\n  [red]✗[/] unrecognized date: {trade_date}")
        con.print("  [dim]try: today · yesterday · 3d · 04-25[/]")
        return
    trade_date = parsed
    if text:
        count = save_thought(root, trade_date, text)
    else:
        content = read_interactive(con, trade_date)
        count = save_thought(root, trade_date, content)
    if count:
        con.print(f"\n  [green]✓[/] saved · {count} {'line' if count == 1 else 'lines'}")
    else:
        con.print("\n  [dim]nothing to save[/]")

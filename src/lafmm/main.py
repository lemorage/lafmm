import os
import shutil
import subprocess

import click

from lafmm.app import LafmmApp
from lafmm.init import HUMAN_DATA, ensure_structure, get_root, scaffold
from lafmm.loader import load_market


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Livermore's Anticipating Future Movements Map."""
    if ctx.invoked_subcommand is not None:
        return

    root = get_root()

    if root is None:
        root = scaffold()
        click.echo(f"created {root}/")
        _launch_claude(root)
        return

    ensure_structure(root)
    human = root / HUMAN_DATA
    mkt = load_market(human)

    if not mkt.groups:
        click.echo(f"no groups found in {human}/")
        click.echo("  add group folders with group.toml + stock CSVs")
        return

    LafmmApp(mkt).run()


# ── Stats subcommand ─────────────────────────────────────────────────


@main.command()
@click.argument("account", required=False)
@click.option("--period", "-p", default=None, help="2026, 2026-Q1, 2026-03, 30d, or start:end")
@click.option("--benchmark/--no-benchmark", default=True, help="Compare against SPY")
def stats(account: str | None, period: str | None, benchmark: bool) -> None:
    """Show trading performance statistics."""
    from lafmm.stats import _resolve_account, _run_compute, render_stats

    root = get_root()
    if root is None:
        click.echo("run 'lafmm' first to set up")
        return

    account_dir = _resolve_account(root / "accounts", account)
    journal = account_dir / "journal"
    if not journal.is_dir() or not any(journal.rglob("*.md")):
        click.echo(f"no trade data in {account_dir.name}/")
        click.echo("  use the sync-trades skill to import broker data first")
        return

    data = _run_compute(root, account_dir, period, benchmark)
    render_stats(data)


# ── Bootstrap ────────────────────────────────────────────────────────


SEED_PROMPT = """\
Fresh setup. profile.md has <!-- PLACEHOLDER --> markers. \
Interview the user to fill it in, then help set up their first trading account.

Rules:
- 2-3 questions per message. Casual tone — conversation, not a form.
- If user says "skip" or "don't know," leave the PLACEHOLDER marker.
- Write the file after user confirms each section. One-line confirmation only.
- If user seems impatient, compress remaining questions or offer to leave placeholders.
- Target: ~2 minutes total.

Sequence:
1. profile.md — experience, risk tolerance, goals, known biases, trading system.
   Open with: "Before we start — a few quick questions so I can tailor analysis to you."
   If no trading system yet, write "No formal system yet — developing" and move on.
2. First account — ask broker name, account type, instruments, fees.
   Create accounts/{name}/ with account.toml, capital/, and journal/ directories.
   account.toml structure:
     [broker]
     name = "{broker name}"
     type = "{account type}"
     instruments = ["{what they trade}"]
     tracked_since = "{today's date}"
     [fees]
     {fee fields from user's answers}
   Adapt to what the user tells you.

After setup, print:
  Profile saved.
    Experience : {summary}
    Risk       : {tolerance}
    System     : {one-line or "not yet defined"}
    Account    : {name} ({broker}, {account type})

Then continue the session, and the user can immediately ask about markets.\
"""


def _launch_claude(root: os.PathLike[str]) -> None:
    claude = shutil.which("claude")
    if claude:
        if click.confirm("launch claude code?", default=True):
            subprocess.run([claude, SEED_PROMPT], cwd=root, check=False)
    else:
        click.echo()
        click.echo("  claude code not found on PATH.")
        click.echo("  install: https://claude.ai/download")
        click.echo(f"  or use any agent CLI: cd {root}")

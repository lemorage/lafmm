import os
import shutil
import subprocess

import click

from lafmm.app import LafmmApp
from lafmm.init import HUMAN_DATA, get_root, scaffold
from lafmm.loader import load_market


@click.command()
def main() -> None:
    """Livermore's Anticipating Future Movements Map."""
    root = get_root()

    if root is None:
        root = scaffold()
        click.echo(f"created {root}/")
        _launch_claude(root)
        return

    human = root / HUMAN_DATA
    mkt = load_market(human)

    if not mkt.groups:
        click.echo(f"no groups found in {human}/")
        click.echo("  add group folders with group.toml + stock CSVs")
        return

    LafmmApp(mkt).run()


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
   Create accounts/{name}/ with account.toml and journal/ directory.

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

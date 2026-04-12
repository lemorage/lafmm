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


def _launch_claude(root: os.PathLike[str]) -> None:
    claude = shutil.which("claude")
    if claude:
        if click.confirm("launch claude code?", default=True):
            subprocess.run([claude], cwd=root, check=False)
    else:
        click.echo()
        click.echo("  claude code not found on PATH.")
        click.echo("  install: https://claude.ai/download")
        click.echo(f"  or use any agent CLI: cd {root}")

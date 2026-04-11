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
        click.echo()
        click.echo("  next steps:")
        click.echo(f"  1. add group folders to {root / HUMAN_DATA}/")
        click.echo(f"  2. cd {root} && claude")
        click.echo("     (or codex, or any agent you prefer)")
        return

    human = root / HUMAN_DATA
    mkt = load_market(human)

    if not mkt.groups:
        click.echo(f"no groups found in {human}/")
        click.echo("  add group folders with group.toml + stock CSVs")
        return

    LafmmApp(mkt).run()

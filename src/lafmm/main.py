import sys
from pathlib import Path

import click

from lafmm.app import LafmmApp
from lafmm.loader import load_group, load_market


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def main(path: Path) -> None:
    """Livermore's Anticipating Future Movements Map.

    Point at a group folder (contains group.toml + CSVs) or a market folder
    (contains group subfolders) and the map renders itself.
    """
    if (path / "group.toml").exists():
        state = load_group(path)
    elif _is_market_dir(path):
        state = load_market(path)
    else:
        click.echo("not a group or market folder")
        click.echo("  group folder needs: group.toml + stock CSVs")
        click.echo("  market folder needs: subdirectories with group.toml")
        sys.exit(1)

    app = LafmmApp(state)
    app.run()


def _is_market_dir(path: Path) -> bool:
    return any((d / "group.toml").exists() for d in path.iterdir() if d.is_dir())

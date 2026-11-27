"""Command line entry point (`rpa`). Commands arrive in later phases."""

import typer

from reddit_analyzer import __version__
from reddit_analyzer.cli import auth, dataset, db, runs

app = typer.Typer(
    name="rpa",
    help="Reddit Post Analyzer: collect, store, build datasets from and analyze Reddit content.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(auth.app, name="auth")
app.add_typer(runs.app, name="runs")
app.add_typer(db.app, name="db")
app.add_typer(dataset.app, name="dataset")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"rpa {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Reddit Post Analyzer."""


if __name__ == "__main__":
    app()

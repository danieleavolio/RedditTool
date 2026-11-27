"""Command line entry point (`rpa`)."""

import typer

from reddit_analyzer import __version__
from reddit_analyzer.cli import auth, collect, collection, dataset, db, export, runs
from reddit_analyzer.cli.common import setup_logging

app = typer.Typer(
    name="rpa",
    help="Reddit Post Analyzer: collect, store, build datasets from and analyze Reddit content.",
    no_args_is_help=True,
    add_completion=True,
)
app.add_typer(auth.app, name="auth")
app.add_typer(collect.app, name="collect")
app.add_typer(collection.app, name="collections")
app.add_typer(runs.app, name="runs")
app.add_typer(dataset.app, name="dataset")
app.add_typer(db.app, name="db")
app.command("export")(export.export_cmd)


@app.command("tui")
def tui_cmd() -> None:
    """Open the terminal UI (needs: pip install "reddit-post-analyzer[tui]")."""
    try:
        from reddit_analyzer.tui.app import run
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".")[0] == "textual":
            typer.echo(
                "Error: the terminal UI needs Textual. "
                'Install it with: pip install "reddit-post-analyzer[tui]"',
                err=True,
            )
            raise typer.Exit(1) from None
        raise
    run()


@app.command("gui")
def gui_cmd(
    port: int = typer.Option(8501, "--port", help="Port of the local web server."),
) -> None:
    """Open the web UI in the browser (needs: pip install "reddit-post-analyzer[gui]")."""
    try:
        from streamlit.web import cli as streamlit_cli

        from reddit_analyzer.gui import streamlit_app
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".")[0] in ("streamlit", "plotly"):
            typer.echo(
                "Error: the web UI needs Streamlit and Plotly. "
                'Install them with: pip install "reddit-post-analyzer[gui]"',
                err=True,
            )
            raise typer.Exit(1) from None
        raise
    streamlit_cli.main_run([streamlit_app.__file__, "--server.port", str(port)])


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"rpa {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only print results and errors (no progress or notes)."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log debug details to stderr."),
) -> None:
    """Reddit Post Analyzer. Put --quiet/--verbose before the command: `rpa -q runs list`."""
    setup_logging(quiet, verbose)


if __name__ == "__main__":
    app()

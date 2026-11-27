"""`rpa runs ...`: list collection runs and resume interrupted ones."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from reddit_analyzer.cli.collect import execute_run
from reddit_analyzer.cli.common import JsonOption, cli_errors, fail, get_ui
from reddit_analyzer.models import ListingParams, RunStatus, SearchParams
from reddit_analyzer.storage import Database

app = typer.Typer(help="List and resume collection runs.", no_args_is_help=True)


def _describe(params: SearchParams | ListingParams) -> str:
    if isinstance(params, SearchParams):
        return params.query
    return f"r/{params.subreddit} ({params.sort})"


@app.command("list")
def list_runs(
    collection: str | None = typer.Option(None, "--collection", "-c", help="Only this collection."),
    status: Annotated[
        RunStatus | None, typer.Option("--status", help="Only runs in this state.")
    ] = None,
    limit: int = typer.Option(20, "--limit", "-n", min=1, help="How many runs to show."),
    json: JsonOption = False,
) -> None:
    """Show recent runs, newest first."""
    ui = get_ui(json)
    with cli_errors(ui), Database.open() as db:
        runs = db.list_runs(collection=collection, status=status, limit=limit)
    if ui.json:
        ui.emit([r.model_dump(mode="json") for r in runs])
        return
    if not runs:
        ui.result("No runs yet.")
        return
    table = Table(box=None)
    table.add_column("ID", justify="right")
    table.add_column("STATUS")
    table.add_column("COLLECTION")
    table.add_column("POSTS", justify="right")
    table.add_column("COMMENTS", justify="right")
    table.add_column("QUERY", overflow="fold")
    for run in runs:
        table.add_row(
            str(run.id),
            run.status.value,
            run.collection,
            str(run.posts_fetched),
            str(run.comments_fetched),
            _describe(run.params),
        )
    ui.table(table)


@app.command()
def resume(
    run_id: int = typer.Argument(..., help="Run ID, see `rpa runs list`."),
    json: JsonOption = False,
) -> None:
    """Continue an interrupted or failed run from its last saved page."""
    ui = get_ui(json)
    with cli_errors(ui), Database.open() as db:
        run = db.get_run(run_id)
        if run is None:
            raise fail(f"Run {run_id} does not exist.")
        if run.status is RunStatus.COMPLETED:
            if ui.json:
                ui.emit(run.model_dump(mode="json"))
            else:
                ui.result(f"Run {run_id} is already completed.")
            return
        ui.info(f"Resuming run {run_id} from {run.posts_fetched} posts ...")
        execute_run(db, run, ui)

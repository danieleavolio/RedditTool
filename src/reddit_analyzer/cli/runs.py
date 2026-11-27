"""`rpa runs ...`: list collection runs and resume interrupted ones."""

from __future__ import annotations

from typing import Annotated

import typer

from reddit_analyzer.collect.runner import Progress, run_collection
from reddit_analyzer.errors import RedditError
from reddit_analyzer.models import ListingParams, RunStatus, SearchParams
from reddit_analyzer.sources.oauth import RedditClient
from reddit_analyzer.storage import Database

app = typer.Typer(help="List and resume collection runs.", no_args_is_help=True)


def _fail(exc: Exception | str) -> typer.Exit:
    typer.echo(f"Error: {exc}", err=True)
    return typer.Exit(1)


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
) -> None:
    """Show recent runs, newest first."""
    try:
        with Database.open() as db:
            runs = db.list_runs(collection=collection, status=status, limit=limit)
    except RedditError as exc:
        raise _fail(exc) from exc
    if not runs:
        typer.echo("No runs yet.")
        return
    typer.echo(f"{'ID':>4}  {'STATUS':<10} {'COLLECTION':<22} {'POSTS':>6} {'COMMENTS':>8}  QUERY")
    for run in runs:
        typer.echo(
            f"{run.id:>4}  {run.status.value:<10} {run.collection:<22} "
            f"{run.posts_fetched:>6} {run.comments_fetched:>8}  {_describe(run.params)}"
        )


def _print_progress(event: Progress) -> None:
    if event.stage == "comments":
        return
    run = event.run
    typer.echo(
        f"page {event.page}: {run.posts_fetched} posts "
        f"({run.posts_inserted} new, {run.posts_updated} updated), "
        f"{run.comments_fetched} comments"
    )
    if event.end_reason == "cap":
        typer.echo(
            "Reddit stops a listing at about 1000 items. To collect more, run again with "
            "a different sort or time window."
        )


@app.command()
def resume(run_id: int = typer.Argument(..., help="Run ID, see `rpa runs list`.")) -> None:
    """Continue an interrupted or failed run from its last saved page."""
    try:
        with Database.open() as db:
            run = db.get_run(run_id)
            if run is None:
                raise _fail(f"Run {run_id} does not exist.")
            if run.status is RunStatus.COMPLETED:
                typer.echo(f"Run {run_id} is already completed.")
                return
            typer.echo(f"Resuming run {run_id} from {run.posts_fetched} posts ...")
            with RedditClient.from_config() as client:
                final = run_collection(db, client, run, on_progress=_print_progress)
    except KeyboardInterrupt:
        typer.echo(f"\nInterrupted. Continue with: rpa runs resume {run_id}", err=True)
        raise typer.Exit(130) from None
    except RedditError as exc:
        typer.echo(f"Continue later with: rpa runs resume {run_id}", err=True)
        raise _fail(exc) from exc
    typer.echo(f"Done: run {final.id} {final.status.value}.")

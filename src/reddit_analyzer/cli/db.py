"""`rpa db ...`: maintenance of the local database."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from reddit_analyzer.errors import RedditError
from reddit_analyzer.storage import Database
from reddit_analyzer.storage.migrate import import_legacy

app = typer.Typer(help="Local database maintenance.", no_args_is_help=True)


@app.command("import-legacy")
def import_legacy_cmd(
    path: Annotated[Path, typer.Argument(help="The old data/reddit_posts.db file.")],
) -> None:
    """Import a pre-0.2 database: one collection per search query. Safe to repeat."""
    try:
        with Database.open() as db:
            result = import_legacy(db, path)
    except RedditError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Imported {result.posts_inserted} new posts into {result.collections} new "
        f"collections ({result.posts_linked} posts linked)."
    )
    if result.skipped_collections:
        typer.echo(f"Already imported, skipped: {', '.join(result.skipped_collections)}")
    if result.skipped_rows:
        typer.echo(f"Skipped {result.skipped_rows} rows without a post id.")
    typer.echo(
        "Note: the old database has no post dates, so the retrieval time was used as the date."
    )

"""`rpa db ...`: maintenance of the local database."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from reddit_analyzer.cli.common import JsonOption, cli_errors, get_ui
from reddit_analyzer.storage import Database
from reddit_analyzer.storage.migrate import import_legacy

app = typer.Typer(help="Local database maintenance.", no_args_is_help=True)


@app.command("import-legacy")
def import_legacy_cmd(
    path: Annotated[Path, typer.Argument(help="The old data/reddit_posts.db file.")],
    json: JsonOption = False,
) -> None:
    """Import a pre-0.2 database: one collection per search query. Safe to repeat."""
    ui = get_ui(json)
    with cli_errors(ui), Database.open() as db:
        result = import_legacy(db, path)
    if ui.json:
        ui.emit(asdict(result))
        return
    ui.result(
        f"Imported {result.posts_inserted} new posts into {result.collections} new "
        f"collections ({result.posts_linked} posts linked)."
    )
    if result.skipped_collections:
        ui.info(f"Already imported, skipped: {', '.join(result.skipped_collections)}")
    if result.skipped_rows:
        ui.info(f"Skipped {result.skipped_rows} rows without a post id.")
    ui.info("Note: the old database has no post dates, so the retrieval time was used as the date.")

"""`rpa collections ...`: what is stored locally."""

from __future__ import annotations

import typer
from rich.table import Table

from reddit_analyzer.cli.common import JsonOption, cli_errors, get_ui
from reddit_analyzer.storage import Database

app = typer.Typer(help="Inspect local collections.", no_args_is_help=True)


@app.command("list")
def list_collections(json: JsonOption = False) -> None:
    """Show every collection with its post and comment counts."""
    ui = get_ui(json)
    with cli_errors(ui), Database.open() as db:
        rows = [
            {
                "name": c.name,
                "posts": db.count_posts(c.name),
                "comments": db.count_comments(c.name),
                "runs": len(db.list_runs(collection=c.name)),
                "created_at": c.created_at.isoformat(),
            }
            for c in db.list_collections()
        ]
    if ui.json:
        ui.emit(rows)
        return
    if not rows:
        ui.result('No collections yet. Start with: rpa collect search "keywords"')
        return
    table = Table(box=None)
    table.add_column("COLLECTION")
    table.add_column("POSTS", justify="right")
    table.add_column("COMMENTS", justify="right")
    table.add_column("RUNS", justify="right")
    for r in rows:
        table.add_row(r["name"], str(r["posts"]), str(r["comments"]), str(r["runs"]))
    ui.table(table)

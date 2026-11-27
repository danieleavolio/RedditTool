"""`rpa analyze`: run analyzers on a collection, or show what was already computed."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from reddit_analyzer import analyzers
from reddit_analyzer.cli.common import JsonOption, cli_errors, get_ui
from reddit_analyzer.models import AnalysisResult
from reddit_analyzer.storage import Database


def _list(ui) -> None:
    rows = [
        {
            "name": a.name,
            "description": a.description,
            "ready": not analyzers.missing_requirements(a),
            "extra": a.extra or None,
        }
        for a in analyzers.available().values()
    ]
    if ui.json:
        ui.emit(rows)
        return
    table = Table(box=None)
    for column in ("ANALYZER", "STATUS", "WHAT IT DOES"):
        table.add_column(column)
    for r in rows:
        status = "ready" if r["ready"] else f"needs [{r['extra'] or 'extra'}]"
        table.add_row(r["name"], status, r["description"])
    ui.table(table)


def analyze_cmd(
    collection: Annotated[
        str | None,
        typer.Argument(help="Collection name (default: the whole database)."),
    ] = None,
    only: Annotated[
        list[str] | None,
        typer.Option("--analyzer", "-a", help="Analyzer to run, repeatable (default: all ready)."),
    ] = None,
    show: Annotated[
        bool, typer.Option("--show", help="Show stored results without computing anything.")
    ] = False,
    list_: Annotated[
        bool, typer.Option("--list", help="List the available analyzers and exit.")
    ] = False,
    json: JsonOption = False,
) -> None:
    """Compute statistics, keywords, languages and sentiment, and store them for the UIs."""
    ui = get_ui(json)
    with cli_errors(ui):
        if list_:
            return _list(ui)
        available = analyzers.available()
        explicit = bool(only)
        names = only or list(available)
        results: list[AnalysisResult] = []
        skipped: dict[str, str] = {}
        with Database.open() as db:
            if show:
                stored = {a.analyzer: a for a in db.list_analyses(collection)}
                results = [stored[n] for n in names if n in stored]
            else:
                for name in names:
                    analyzer = analyzers.get(name)  # unknown name: error with the valid ones
                    if analyzers.missing_requirements(analyzer) and not explicit:
                        skipped[name] = analyzers.install_hint(analyzer)
                        continue
                    ui.info(f"running {name} ...")
                    results.append(analyzers.run(db, name, collection))
    if ui.json:
        ui.emit(
            {
                "collection": collection,
                "results": {
                    r.analyzer: {"computed_at": r.computed_at, "data": r.data} for r in results
                },
                "skipped": skipped,
            }
        )
        return
    for r in results:
        ui.result(f"== {r.analyzer} ({r.computed_at:%Y-%m-%d %H:%M} UTC)")
        ui.result(analyzers.get(r.analyzer).summary(r.data))
    if show and not results:
        ui.result("Nothing stored yet. Run: rpa analyze " + (collection or ""))
    for hint in skipped.values():
        ui.info(f"skipped: {hint}")

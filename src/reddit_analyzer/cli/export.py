"""`rpa export`: write a whole collection to CSV, JSONL, Parquet or Hugging Face format."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from reddit_analyzer.cli.common import (
    FormatChoice,
    JsonOption,
    UnitChoice,
    cli_errors,
    fail,
    get_ui,
)
from reddit_analyzer.cli.dataset import stats_dict
from reddit_analyzer.datasets.builder import build
from reddit_analyzer.datasets.recipe import Output, Recipe
from reddit_analyzer.storage import Database


def export_cmd(
    collection: Annotated[str, typer.Argument(help="Collection name, see `rpa collections list`.")],
    format: Annotated[FormatChoice, typer.Option("--format", "-f")] = "jsonl",
    unit: Annotated[
        UnitChoice, typer.Option("--unit", help="Rows are posts, comments or post/reply pairs.")
    ] = "post",
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Output folder (default: out/<collection>).")
    ] = None,
    json: JsonOption = False,
) -> None:
    """Export a collection as it is, with default columns. For filters use `rpa dataset build`."""
    ui = get_ui(json)
    with cli_errors(ui), Database.open() as db:
        try:
            recipe = Recipe(
                name=collection,
                collection=collection,
                unit=unit.value,
                output=Output(format=format.value),
            )
        except ValidationError:
            raise fail(f"{collection!r} is not a valid collection name.") from None
        result = build(recipe, db, out or Path("out") / collection)
    if ui.json:
        ui.emit(
            {
                "files": [str(p) for p in result.files],
                "card": str(result.card),
                "stats": stats_dict(result.stats),
            }
        )
        return
    ui.info(f"{result.stats.kept} rows exported")
    for path in [*result.files, result.card]:
        ui.result(f"wrote {path}")

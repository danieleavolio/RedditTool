"""`rpa dataset ...`: build datasets from recipes and preview them."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from reddit_analyzer.cli.common import JsonOption, Ui, cli_errors, get_ui
from reddit_analyzer.datasets.builder import Stats, build, preview
from reddit_analyzer.datasets.recipe import Recipe, load_recipe
from reddit_analyzer.storage import Database

app = typer.Typer(help="Build datasets from YAML recipes.", no_args_is_help=True)

RecipeArg = Annotated[Path, typer.Argument(help="A recipe file, see recipes/examples/.")]


def stats_dict(stats: Stats) -> dict:
    return {
        "seen": stats.seen,
        "kept": stats.kept,
        "dropped": dict(stats.dropped),
        "parts": dict(stats.parts),
        "chars_mean": round(stats.chars_mean, 1),
        "chars_max": stats.chars_max,
    }


def _print_stats(ui: Ui, stats: Stats, recipe: Recipe) -> None:
    ui.info(f"{stats.kept} rows kept out of {stats.seen} {recipe.unit} candidates")
    for reason, count in stats.dropped.most_common():
        ui.info(f"  dropped {count:>6}  {reason}")
    if recipe.split:
        ui.info("  parts: " + ", ".join(f"{n} {stats.parts[n]}" for n in recipe.split.parts))
    if stats.kept:
        ui.info(f"  text: {stats.chars_mean:.0f} characters on average, {stats.chars_max} at most")


@app.command("build")
def build_cmd(
    recipe_path: RecipeArg,
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Output folder (default: out/<name>).")
    ] = None,
    json: JsonOption = False,
) -> None:
    """Write the dataset and its dataset_card.md."""
    ui = get_ui(json)
    with cli_errors(ui):
        recipe = load_recipe(recipe_path)
        with Database.open() as db:
            result = build(recipe, db, out or Path("out") / recipe.name)
    if ui.json:
        ui.emit(
            {
                "files": [str(p) for p in result.files],
                "card": str(result.card),
                "stats": stats_dict(result.stats),
            }
        )
        return
    _print_stats(ui, result.stats, recipe)
    for path in [*result.files, result.card]:
        ui.result(f"wrote {path}")


@app.command("preview")
def preview_cmd(
    recipe_path: RecipeArg,
    n: Annotated[int, typer.Option("--n", "-n", min=1, help="Rows to show.")] = 20,
    json: JsonOption = False,
) -> None:
    """Show the first rows and statistics, without writing anything."""
    ui = get_ui(json)
    with cli_errors(ui):
        recipe = load_recipe(recipe_path)
        with Database.open() as db:
            result = preview(recipe, db, n)
    if ui.json:
        ui.emit({"rows": result.rows, "stats": stats_dict(result.stats)})
        return
    _print_stats(ui, result.stats, recipe)
    for row in result.rows:
        text = " ".join(row["text"].split())
        ui.result(f"- [{row['subreddit']} {row['score']:>5}] {text[:100]}")

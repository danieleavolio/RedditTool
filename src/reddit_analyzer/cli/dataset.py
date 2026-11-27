"""`rpa dataset ...`: build datasets from recipes and preview them."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from reddit_analyzer.datasets.builder import Stats, build, preview
from reddit_analyzer.datasets.recipe import Recipe, load_recipe
from reddit_analyzer.errors import RedditError
from reddit_analyzer.storage import Database

app = typer.Typer(help="Build datasets from YAML recipes.", no_args_is_help=True)

RecipeArg = Annotated[Path, typer.Argument(help="A recipe file, see recipes/examples/.")]


def _fail(exc: Exception) -> typer.Exit:
    typer.echo(f"Error: {exc}", err=True)
    return typer.Exit(1)


def _print_stats(stats: Stats, recipe: Recipe) -> None:
    typer.echo(f"{stats.kept} rows kept out of {stats.seen} {recipe.unit} candidates")
    for reason, count in stats.dropped.most_common():
        typer.echo(f"  dropped {count:>6}  {reason}")
    if recipe.split:
        typer.echo("  parts: " + ", ".join(f"{n} {stats.parts[n]}" for n in recipe.split.parts))
    if stats.kept:
        typer.echo(
            f"  text: {stats.chars_mean:.0f} characters on average, {stats.chars_max} at most"
        )


@app.command("build")
def build_cmd(
    recipe_path: RecipeArg,
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Output folder (default: out/<name>).")
    ] = None,
) -> None:
    """Write the dataset and its dataset_card.md."""
    try:
        recipe = load_recipe(recipe_path)
        with Database.open() as db:
            result = build(recipe, db, out or Path("out") / recipe.name)
    except RedditError as exc:
        raise _fail(exc) from exc
    _print_stats(result.stats, recipe)
    for path in [*result.files, result.card]:
        typer.echo(f"wrote {path}")


@app.command("preview")
def preview_cmd(
    recipe_path: RecipeArg,
    n: Annotated[int, typer.Option("--n", "-n", min=1, help="Rows to show.")] = 20,
) -> None:
    """Show the first rows and statistics, without writing anything."""
    try:
        recipe = load_recipe(recipe_path)
        with Database.open() as db:
            result = preview(recipe, db, n)
    except RedditError as exc:
        raise _fail(exc) from exc
    _print_stats(result.stats, recipe)
    for row in result.rows:
        text = " ".join(row["text"].split())
        typer.echo(f"- [{row['subreddit']} {row['score']:>5}] {text[:100]}")

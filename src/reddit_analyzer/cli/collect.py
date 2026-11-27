"""`rpa collect ...`: download posts (and comments) from Reddit into a collection."""

from __future__ import annotations

import re
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from reddit_analyzer.cli.common import (
    JsonOption,
    ListingSortChoice,
    SortChoice,
    TimeChoice,
    Ui,
    cli_errors,
    get_ui,
)
from reddit_analyzer.collect.runner import Progress as RunProgress
from reddit_analyzer.collect.runner import run_collection
from reddit_analyzer.config import load_settings
from reddit_analyzer.models import CommentsSpec, ListingParams, Run, SearchParams
from reddit_analyzer.sources.base import EndReason
from reddit_analyzer.sources.oauth import RedditClient
from reddit_analyzer.storage import Database

app = typer.Typer(help="Collect posts and comments from Reddit.", no_args_is_help=True)

CAP_NOTE = (
    "Reddit stops a listing at about 1000 items. To collect more, run again with "
    "a different sort or time window."
)

CollectionOpt = Annotated[
    str | None,
    typer.Option("--collection", "-c", help="Collection to add to (default: derived from input)."),
]
LimitOpt = Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of posts.")]
CommentsOpt = Annotated[
    bool, typer.Option("--comments", help="Also download the comments of every post.")
]
DepthOpt = Annotated[
    int | None, typer.Option("--depth", min=1, help="Comment depth (default: from config).")
]
MaxPerPostOpt = Annotated[
    int | None,
    typer.Option("--max-per-post", min=1, help="Comments per post (default: from config)."),
]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:64].strip("-")
    return slug or "collection"


class RunReporter:
    """Shows progress while a run executes: a bar on a terminal, one line per page otherwise."""

    def __init__(self, ui: Ui, limit: int):
        self.ui = ui
        self.limit = limit
        self.end_reason: EndReason | None = None
        self._console = Console(stderr=True)
        self._bar: Progress | None = None
        self._task = None

    def __enter__(self) -> RunReporter:
        if self.ui.talkative and self._console.is_terminal:
            self._bar = Progress(
                TextColumn("[bold]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total} posts"),
                TimeElapsedColumn(),
                console=self._console,
                transient=True,
            )
            self._bar.start()
            self._task = self._bar.add_task("Collecting", total=self.limit)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._bar:
            self._bar.stop()

    def __call__(self, event: RunProgress) -> None:
        run = event.run
        if event.stage == "posts":
            self.end_reason = event.end_reason or self.end_reason
        if self._bar is not None:
            if event.stage == "comments":
                self._bar.update(self._task, description=f"Comments for {event.post_id}")
            else:
                self._bar.update(self._task, completed=run.posts_fetched, description="Collecting")
            return
        if event.stage == "comments":
            return
        self.ui.info(
            f"page {event.page}: {run.posts_fetched} posts "
            f"({run.posts_inserted} new, {run.posts_updated} updated), "
            f"{run.comments_fetched} comments"
        )


def execute_run(db: Database, run: Run, ui: Ui) -> Run:
    """Run (or resume) ``run`` against Reddit, report progress, print the outcome."""
    assert run.id is not None
    ui.hint = f"Continue later with: rpa runs resume {run.id}"
    with RedditClient.from_config() as client, RunReporter(ui, run.params.limit) as reporter:
        final = run_collection(db, client, run, on_progress=reporter)
    ui.hint = None
    capped = reporter.end_reason == "cap"
    if ui.json:
        ui.emit({**final.model_dump(mode="json"), "end_reason": reporter.end_reason})
        return final
    if capped:
        ui.info(CAP_NOTE)
    ui.result(
        f"Done: run {final.id} {final.status.value}, {final.posts_fetched} posts "
        f"({final.posts_inserted} new), {final.comments_fetched} comments "
        f"in collection {final.collection!r}."
    )
    return final


def _comments(enabled: bool, depth: int | None, max_per_post: int | None) -> CommentsSpec | None:
    if not enabled:
        return None
    cfg = load_settings().collect
    return CommentsSpec(
        depth=depth or cfg.comments_depth, max_per_post=max_per_post or cfg.comments_max_per_post
    )


@app.command("search")
def search_cmd(
    query: Annotated[str, typer.Argument(help="Keywords to search for.")],
    subreddit: Annotated[
        list[str] | None,
        typer.Option("--subreddit", "-s", help="Limit to a subreddit (repeatable)."),
    ] = None,
    sort: Annotated[SortChoice, typer.Option("--sort", help="Result order.")] = "relevance",
    time: Annotated[TimeChoice, typer.Option("--time", "-t", help="Time window.")] = "all",
    limit: LimitOpt = 100,
    comments: CommentsOpt = False,
    depth: DepthOpt = None,
    max_per_post: MaxPerPostOpt = None,
    collection: CollectionOpt = None,
    json: JsonOption = False,
) -> None:
    """Search Reddit (all of it, or the given subreddits) and store the posts."""
    ui = get_ui(json)
    with cli_errors(ui):
        params = SearchParams(
            query=query,
            subreddits=subreddit or [],
            sort=sort.value,
            time=time.value,
            limit=limit,
            comments=_comments(comments, depth, max_per_post),
        )
        with Database.open() as db:
            run = db.create_run(Run(collection=collection or slugify(query), params=params))
            ui.info(f"Run {run.id} in collection {run.collection!r}: searching {query!r} ...")
            execute_run(db, run, ui)


@app.command("subreddit")
def subreddit_cmd(
    name: Annotated[str, typer.Argument(help="Subreddit name, with or without r/.")],
    sort: Annotated[ListingSortChoice, typer.Option("--sort", help="Listing to read.")] = "new",
    time: Annotated[
        TimeChoice, typer.Option("--time", "-t", help="Time window (top and controversial).")
    ] = "all",
    limit: LimitOpt = 100,
    comments: CommentsOpt = False,
    depth: DepthOpt = None,
    max_per_post: MaxPerPostOpt = None,
    collection: CollectionOpt = None,
    json: JsonOption = False,
) -> None:
    """Read a subreddit's hot/new/top/rising/controversial listing and store the posts."""
    ui = get_ui(json)
    with cli_errors(ui):
        params = ListingParams(
            subreddit=name,
            sort=sort.value,
            time=time.value,
            limit=limit,
            comments=_comments(comments, depth, max_per_post),
        )
        with Database.open() as db:
            run = db.create_run(
                Run(collection=collection or slugify(params.subreddit), params=params)
            )
            ui.info(
                f"Run {run.id} in collection {run.collection!r}: reading r/{params.subreddit} ..."
            )
            execute_run(db, run, ui)

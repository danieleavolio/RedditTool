"""New collection: a form that starts a run in a worker, with live log, progress and cancel."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError
from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
)
from textual.worker import get_current_worker

from reddit_analyzer.cli.collect import CAP_NOTE
from reddit_analyzer.collect.runner import Progress
from reddit_analyzer.errors import RedditError
from reddit_analyzer.models import (
    CommentsSpec,
    ListingParams,
    ListingSort,
    Run,
    SearchParams,
    Sort,
    TimeFilter,
)

if TYPE_CHECKING:
    from reddit_analyzer.tui.app import RpaApp

SEARCH, LISTING = "search", "listing"
SORTS = {SEARCH: get_args(Sort), LISTING: get_args(ListingSort)}
DEFAULT_SORT = {SEARCH: "relevance", LISTING: "new"}


def _options(values: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(v, v) for v in values]


class CollectScreen(Screen):
    app: RpaApp  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._cancel_event = threading.Event()
        self._collecting = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="collect-form"):
            yield Label("New collection", classes="pane-title")
            with Horizontal(classes="form-row"):
                yield Label("Source")
                yield Select(
                    [("Search by keywords", SEARCH), ("Subreddit listing", LISTING)],
                    value=SEARCH,
                    allow_blank=False,
                    compact=True,
                    id="kind",
                )
            with Horizontal(classes="form-row"):
                yield Label("Keywords", id="query-label")
                yield Input(placeholder="what to search for", compact=True, id="query")
            with Horizontal(classes="form-row", id="subs-row"):
                yield Label("Subreddits")
                yield Input(
                    placeholder="optional, comma separated: python, rust", compact=True, id="subs"
                )
            with Horizontal(classes="form-row"):
                yield Label("Sort")
                yield Select(
                    _options(SORTS[SEARCH]),
                    value="relevance",
                    allow_blank=False,
                    compact=True,
                    id="sort",
                )
            with Horizontal(classes="form-row"):
                yield Label("Time window")
                yield Select(
                    _options(get_args(TimeFilter)),
                    value="all",
                    allow_blank=False,
                    compact=True,
                    id="time",
                )
            with Horizontal(classes="form-row"):
                yield Label("Max posts")
                yield Input("100", type="integer", compact=True, id="limit")
            with Horizontal(classes="form-row"):
                yield Label("Comments")
                yield Checkbox("download comments too", compact=True, id="comments")
            with Horizontal(classes="form-row"):
                yield Label("Collection")
                yield Input(
                    placeholder="optional, default derived from the input", compact=True, id="name"
                )
        with Horizontal(id="collect-buttons"):
            yield Button("Start", variant="success", compact=True, id="start")
            yield Button("Cancel", variant="error", compact=True, id="cancel", disabled=True)
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield Static("", id="status", classes="note")
        yield RichLog(id="collect-log", wrap=True, markup=False)
        yield Footer()

    def on_screen_resume(self) -> None:
        run_id, self.app.pending_resume = self.app.pending_resume, None
        if run_id is not None and not self._collecting:
            run = self.app.service.get_run(run_id)
            if run is not None:
                self._launch(run, resumed=True)

    # -- Form -----------------------------------------------------------------------------

    @on(Select.Changed, "#kind")
    def _kind_changed(self, event: Select.Changed) -> None:
        kind = str(event.value)
        label = "Keywords" if kind == SEARCH else "Subreddit"
        self.query_one("#query-label", Label).update(label)
        self.query_one("#subs-row").display = kind == SEARCH
        sort = self.query_one("#sort", Select)
        sort.set_options(_options(SORTS[kind]))
        sort.value = DEFAULT_SORT[kind]

    @on(Button.Pressed, "#start")
    def _start_pressed(self) -> None:
        if self._collecting:
            return
        try:
            run = self.app.service.create_run(self._run_from_form())
        except (ValidationError, ValueError) as exc:
            self.notify(self._explain(exc), severity="error", title="Check the form")
            return
        self._launch(run, resumed=False)

    @on(Button.Pressed, "#cancel")
    def _cancel_pressed(self) -> None:
        self._cancel_event.set()
        self.query_one("#cancel", Button).disabled = True
        self.query_one("#status", Static).update("Cancelling after the current step ...")

    @staticmethod
    def _explain(exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            return "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'form'}: {e['msg']}" for e in exc.errors()
            )
        return str(exc)

    def _run_from_form(self) -> Run:
        kind = str(self.query_one("#kind", Select).value)
        text = self.query_one("#query", Input).value.strip()
        if not text:
            raise ValueError("Type the keywords or the subreddit first.")
        limit_text = self.query_one("#limit", Input).value
        limit = int(limit_text) if limit_text.strip() else 100
        sort = str(self.query_one("#sort", Select).value)
        time = str(self.query_one("#time", Select).value)
        comments = None
        if self.query_one("#comments", Checkbox).value:
            cfg = self.app.service.settings.collect
            comments = CommentsSpec(
                depth=cfg.comments_depth, max_per_post=cfg.comments_max_per_post
            )
        if kind == SEARCH:
            subs = [
                s for s in (p.strip() for p in self.query_one("#subs", Input).value.split(",")) if s
            ]
            params: SearchParams | ListingParams = SearchParams(
                query=text, subreddits=subs, sort=sort, time=time, limit=limit, comments=comments
            )
        else:
            params = ListingParams(
                subreddit=text, sort=sort, time=time, limit=limit, comments=comments
            )
        name = self.query_one("#name", Input).value.strip()
        seed = text if kind == SEARCH else params.subreddit
        return Run(collection=name or self.app.service.default_collection(seed), params=params)

    # -- Running --------------------------------------------------------------------------

    def _launch(self, run: Run, resumed: bool) -> None:
        self._collecting = True
        self._cancel_event.clear()
        self.query_one("#start", Button).disabled = True
        self.query_one("#cancel", Button).disabled = False
        bar = self.query_one("#progress", ProgressBar)
        bar.update(total=run.params.limit, progress=run.posts_fetched)
        log = self.query_one("#collect-log", RichLog)
        verb = "Resuming" if resumed else "Starting"
        log.write(f"{verb} run {run.id} in collection {run.collection!r}")
        self.query_one("#status", Static).update(f"Run {run.id} is running ...")
        self._work(run)

    @work(thread=True, exclusive=True, group="collect", exit_on_error=False)
    def _work(self, run: Run) -> None:
        worker = get_current_worker()

        def progress(event: Progress) -> None:
            self.app.call_from_thread(self._on_progress, event)

        try:
            final = self.app.service.execute_run(
                run, progress, lambda: self._cancel_event.is_set() or worker.is_cancelled
            )
        except RedditError as exc:
            self.app.call_from_thread(self._finished, None, str(exc), run)
        else:
            self.app.call_from_thread(self._finished, final, None, run)

    def _on_progress(self, event: Progress) -> None:
        run = event.run
        status = self.query_one("#status", Static)
        if event.stage == "comments":
            status.update(Text(f"Run {run.id}: comments of post {event.post_id} ..."))
            return
        self.query_one("#progress", ProgressBar).update(progress=run.posts_fetched)
        self.query_one("#collect-log", RichLog).write(
            f"page {event.page}: {run.posts_fetched} posts "
            f"({run.posts_inserted} new, {run.posts_updated} updated), "
            f"{run.comments_fetched} comments"
        )
        if event.end_reason == "cap":
            self.query_one("#collect-log", RichLog).write(CAP_NOTE)

    def _finished(self, final: Run | None, error: str | None, run: Run) -> None:
        self._collecting = False
        self.query_one("#start", Button).disabled = False
        self.query_one("#cancel", Button).disabled = True
        log = self.query_one("#collect-log", RichLog)
        status = self.query_one("#status", Static)
        if error is not None:
            log.write(Text(f"Error: {error}", style="bold red"))
            log.write(f"Continue later from the dashboard (u) or with: rpa runs resume {run.id}")
            status.update(Text(f"Run {run.id} failed."))
            self.notify(error, severity="error", title="Run failed")
            return
        assert final is not None
        message = (
            f"Run {final.id} {final.status.value}: {final.posts_fetched} posts "
            f"({final.posts_inserted} new), {final.comments_fetched} comments "
            f"in collection {final.collection!r}."
        )
        log.write(message)
        status.update(Text(message))
        self.app.collection = final.collection
        self.notify(message, title="Collection")

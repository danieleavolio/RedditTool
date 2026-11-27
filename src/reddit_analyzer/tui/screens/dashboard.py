"""Dashboard: collections, recent runs and the state of the Reddit API credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from reddit_analyzer.errors import RedditError
from reddit_analyzer.models import ListingParams, Run, RunStatus

if TYPE_CHECKING:
    from reddit_analyzer.tui.app import RpaApp


def describe(run: Run) -> str:
    params = run.params
    if isinstance(params, ListingParams):
        return f"r/{params.subreddit} ({params.sort})"
    return params.query


class DashboardScreen(Screen):
    app: RpaApp  # type: ignore[assignment]

    BINDINGS = [
        Binding("r", "reload", "Refresh"),
        Binding("v", "check_api", "Check API"),
        Binding("u", "resume_run", "Resume run"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Reddit API: not checked (press v)", id="api-status", classes="note")
        yield Label("Collections (Enter opens it in the browser)", classes="pane-title")
        yield DataTable(id="collections", cursor_type="row", zebra_stripes=True)
        yield Label("Recent runs", classes="pane-title")
        yield DataTable(id="runs", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#collections", DataTable).add_columns(
            "Collection", "Posts", "Comments", "Runs"
        )
        self.query_one("#runs", DataTable).add_columns(
            "ID", "Status", "Collection", "Posts", "Comments", "Query"
        )

    def on_screen_resume(self) -> None:
        self.action_reload()

    def action_reload(self) -> None:
        collections = self.query_one("#collections", DataTable)
        runs = self.query_one("#runs", DataTable)
        collections.clear()
        runs.clear()
        for c in self.app.service.overview():
            collections.add_row(c.name, str(c.posts), str(c.comments), str(c.runs), key=c.name)
        for run in self.app.service.recent_runs():
            runs.add_row(
                str(run.id),
                run.status.value,
                run.collection,
                str(run.posts_fetched),
                str(run.comments_fetched),
                describe(run),
                key=str(run.id),
            )
        if not collections.row_count:
            self.query_one("#api-status", Static).update(
                "No collections yet. Press F2 to start a collection."
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "collections" and event.row_key.value:
            self.app.collection = event.row_key.value
            self.app.switch_mode("browser")

    def action_resume_run(self) -> None:
        runs = self.query_one("#runs", DataTable)
        if not runs.row_count:
            return
        run_id = int(runs.coordinate_to_cell_key(runs.cursor_coordinate).row_key.value or 0)
        run = self.app.service.get_run(run_id)
        if run is None or run.status is RunStatus.COMPLETED:
            self.notify("That run is already completed.", severity="warning")
            return
        self.app.pending_resume = run_id
        self.app.switch_mode("collect")

    def action_check_api(self) -> None:
        self.query_one("#api-status", Static).update("Reddit API: checking ...")
        self._check_api()

    @work(thread=True, exclusive=True, group="api")
    def _check_api(self) -> None:
        try:
            status = self.app.service.auth_status()
        except RedditError as exc:
            text = f"Reddit API: {exc}"
        else:
            remaining = status.ratelimit_remaining
            quota = "unknown" if remaining is None else f"{remaining:.0f}"
            text = f"Reddit API: OK as u/{status.username}, requests left in this window: {quota}"
        self.app.call_from_thread(self.query_one("#api-status", Static).update, Text(text))

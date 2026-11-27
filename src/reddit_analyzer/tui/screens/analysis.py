"""Analysis: statistics of a collection in tables and a sparkline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Select, Sparkline, Static

from reddit_analyzer import analyzers
from reddit_analyzer.errors import RedditError
from reddit_analyzer.models import AnalysisResult
from reddit_analyzer.stats import CollectionStats
from reddit_analyzer.tui.screens.common import ALL, CollectionPicker

if TYPE_CHECKING:
    from reddit_analyzer.tui.app import RpaApp


class AnalysisScreen(CollectionPicker):
    app: RpaApp  # type: ignore[assignment]
    BINDINGS = [Binding("a", "run_analyzers", "Compute analyses")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="analysis-bar"):
            yield Select(
                [("All collections", ALL)], value=ALL, allow_blank=False, compact=True, id="a-coll"
            )
        yield Static("", id="analysis-summary")
        yield Label("Posts per month", classes="pane-title")
        yield Sparkline([], id="months")
        with Horizontal(id="analysis-body"):
            with Vertical():
                yield Label("Top subreddits", classes="pane-title")
                yield DataTable(id="t-subs", cursor_type="row")
            with Vertical():
                yield Label("Top authors", classes="pane-title")
                yield DataTable(id="t-authors", cursor_type="row")
            with Vertical():
                yield Label("Frequent words", classes="pane-title")
                yield DataTable(id="t-words", cursor_type="row")
        yield Label("Saved analyses (press A to compute)", classes="pane-title")
        yield Static("", id="analyzers-text")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#t-subs", DataTable).add_columns("Subreddit", "Posts")
        self.query_one("#t-authors", DataTable).add_columns("Author", "Posts")
        self.query_one("#t-words", DataTable).add_columns("Word", "Count")

    def on_screen_resume(self) -> None:
        select = self.query_one("#a-coll", Select)
        options = [("All collections", ALL)] + [
            (c.name, c.name) for c in self.app.service.overview()
        ]
        wanted = self.app.collection or ALL
        self.fill_select(select, options, wanted)
        self._refresh()

    @on(Select.Changed, "#a-coll")
    def _changed(self, event: Select.Changed) -> None:
        if self._syncing:
            return
        self.app.collection = str(event.value) or None
        self._refresh()

    def _refresh(self) -> None:
        self.query_one("#analysis-summary", Static).update("Computing ...")
        self._compute(str(self.query_one("#a-coll", Select).value) or None)

    @work(thread=True, exclusive=True, group="stats", exit_on_error=False)
    def _compute(self, collection: str | None) -> None:
        stats = self.app.service.stats(collection)
        saved = self.app.service.saved_analyses(collection)
        self.app.call_from_thread(self._show, stats)
        self.app.call_from_thread(self._show_saved, saved)

    def action_run_analyzers(self) -> None:
        self.query_one("#analyzers-text", Static).update("Computing ...")
        self._run_all(str(self.query_one("#a-coll", Select).value) or None)

    @work(thread=True, exclusive=True, group="analyzers", exit_on_error=False)
    def _run_all(self, collection: str | None) -> None:
        """Run every analyzer whose optional dependencies are installed; report the rest."""
        service = self.app.service
        notes = []
        for name, analyzer in service.analyzers().items():
            if name == "stats":  # shown live above
                continue
            if analyzers.missing_requirements(analyzer):
                notes.append(analyzers.install_hint(analyzer))
                continue
            try:
                service.run_analyzer(name, collection)
            except RedditError as exc:
                notes.append(f"{name}: {exc}")
        saved = service.saved_analyses(collection)
        self.app.call_from_thread(self._show_saved, saved, notes)

    def _show_saved(self, saved: dict[str, AnalysisResult], notes: list[str] | None = None) -> None:
        lines = []
        for name, analyzer in self.app.service.analyzers().items():
            if name in saved and name != "stats":
                lines.append(f"{name}: {analyzer.summary(saved[name].data)}")
        lines += notes or []
        self.query_one("#analyzers-text", Static).update(
            Text("\n".join(lines) or "Nothing computed yet.")
        )

    def _show(self, stats: CollectionStats) -> None:
        if not stats.posts:
            summary = "No posts in this collection yet."
        else:
            summary = (
                f"{stats.posts} posts, {stats.comments} comments, "
                f"{stats.first_post} to {stats.last_post}, mean score {stats.score_mean:.1f}"
            )
        self.query_one("#analysis-summary", Static).update(Text(summary))
        self.query_one("#months", Sparkline).data = [float(n) for _, n in stats.posts_per_month]
        for table_id, rows in (
            ("#t-subs", stats.top_subreddits),
            ("#t-authors", stats.top_authors),
            ("#t-words", stats.top_words),
        ):
            table = self.query_one(table_id, DataTable)
            table.clear()
            for name, count in rows:
                table.add_row(name, str(count))

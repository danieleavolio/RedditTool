"""Dataset: edit a YAML recipe with live validation and preview, then build it."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)
from textual.worker import get_current_worker

from reddit_analyzer.datasets.builder import Stats
from reddit_analyzer.errors import RedditError
from reddit_analyzer.service import TEMPLATE, find_recipes
from reddit_analyzer.tui.screens.common import CollectionPicker

if TYPE_CHECKING:
    from reddit_analyzer.tui.app import RpaApp

NEW = ""  # the Select value for "start from a template"
DEBOUNCE_SECONDS = 0.6


def summarize(stats: Stats, unit: str, parts: list[str]) -> str:
    lines = [f"{stats.kept} rows kept out of {stats.seen} {unit} candidates"]
    lines += [f"  dropped {n:>6}  {reason}" for reason, n in stats.dropped.most_common()]
    if parts:
        lines.append("  parts: " + ", ".join(f"{p} {stats.parts[p]}" for p in parts))
    if stats.kept:
        lines.append(f"  text: {stats.chars_mean:.0f} characters on average, {stats.chars_max} max")
    return "\n".join(lines)


class DatasetScreen(CollectionPicker):
    app: RpaApp  # type: ignore[assignment]

    BINDINGS = [("ctrl+b", "build", "Build"), ("ctrl+s", "save", "Save recipe")]

    def __init__(self) -> None:
        super().__init__()
        self._debounce: Timer | None = None
        self._files: dict[str, Path] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="dataset-bar"):
            yield Select(
                [("New recipe from template", NEW)],
                value=NEW,
                allow_blank=False,
                compact=True,
                id="d-file",
            )
            yield Button("Build", variant="success", compact=True, id="d-build")
        with Horizontal(id="dataset-body"):
            with Vertical(id="editor-col"):
                yield Label("Recipe (YAML)", classes="pane-title")
                yield TextArea("", id="recipe-editor", show_line_numbers=True)
                with Horizontal(id="dataset-save"):
                    yield Input("recipes/my-dataset.yaml", compact=True, id="d-path")
                    yield Button("Save", compact=True, id="d-save")
            with Vertical(id="result-col"):
                yield Label("Preview", classes="pane-title")
                yield Static("", id="recipe-status")
                yield DataTable(id="preview-rows", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#preview-rows", DataTable).add_columns("Subreddit", "Score", "Text")
        self.query_one("#recipe-editor", TextArea).load_text(self._template())

    def on_screen_resume(self) -> None:
        self._files = {str(p): p for p in find_recipes(Path.cwd())}
        select = self.query_one("#d-file", Select)
        options = [("New recipe from template", NEW)] + [
            (str(p.relative_to(Path.cwd())), key) for key, p in self._files.items()
        ]
        self.fill_select(select, options, str(select.value))
        self._schedule_preview()

    def _template(self) -> str:
        collection = self.app.collection
        if collection is None:
            rows = self.app.service.overview()
            collection = rows[0].name if rows else "my-collection"
        return TEMPLATE.format(collection=collection)

    # -- Editing --------------------------------------------------------------------------

    @on(Select.Changed, "#d-file")
    def _file_chosen(self, event: Select.Changed) -> None:
        if self._syncing:
            return
        editor = self.query_one("#recipe-editor", TextArea)
        key = str(event.value)
        if key == NEW:
            editor.load_text(self._template())
        else:
            path = self._files[key]
            editor.load_text(path.read_text(encoding="utf-8"))
            self.query_one("#d-path", Input).value = str(path.relative_to(Path.cwd()))
        self._schedule_preview()

    @on(TextArea.Changed, "#recipe-editor")
    def _edited(self) -> None:
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        if self._debounce is not None:
            self._debounce.stop()
        self._debounce = self.set_timer(DEBOUNCE_SECONDS, self._preview)

    def _text(self) -> str:
        return self.query_one("#recipe-editor", TextArea).text

    # -- Preview and build ----------------------------------------------------------------

    @work(thread=True, exclusive=True, group="preview", exit_on_error=False)
    def _preview(self) -> None:
        text = self._text()
        worker = get_current_worker()
        try:
            recipe, result = self.app.service.preview_recipe(text)
        except RedditError as exc:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._show_error, str(exc))
            return
        parts = list(recipe.split.parts) if recipe.split else []
        if not worker.is_cancelled:
            self.app.call_from_thread(
                self._show_preview, summarize(result.stats, recipe.unit, parts), result.rows
            )

    def _show_error(self, message: str) -> None:
        self.query_one("#recipe-status", Static).update(Text(message, style="red"))
        self.query_one("#preview-rows", DataTable).clear()

    def _show_preview(self, summary: str, rows: list[dict]) -> None:
        self.query_one("#recipe-status", Static).update(Text(summary))
        table = self.query_one("#preview-rows", DataTable)
        table.clear()
        for row in rows:
            table.add_row(
                str(row.get("subreddit", "")),
                str(row.get("score", "")),
                " ".join(str(row.get("text", "")).split())[:200],
            )

    @on(Button.Pressed, "#d-build")
    def action_build(self) -> None:
        self.query_one("#d-build", Button).disabled = True
        self._build(self._text())

    @work(thread=True, exclusive=True, group="build", exit_on_error=False)
    def _build(self, text: str) -> None:
        try:
            _, result = self.app.service.build_recipe(text)
        except RedditError as exc:
            self.app.call_from_thread(self._build_done, None, str(exc))
        else:
            self.app.call_from_thread(self._build_done, result, None)

    def _build_done(self, result, error: str | None) -> None:
        self.query_one("#d-build", Button).disabled = False
        if error is not None:
            self.notify(error, severity="error", title="Build failed")
            return
        files = ", ".join(str(p) for p in [*result.files, result.card])
        self.notify(f"{result.stats.kept} rows written: {files}", title="Dataset built", timeout=10)

    @on(Button.Pressed, "#d-save")
    def action_save(self) -> None:
        path = Path(self.query_one("#d-path", Input).value.strip())
        if not path.name:
            self.notify("Type a file name first.", severity="error")
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._text(), encoding="utf-8", newline="\n")
        except OSError as exc:
            self.notify(f"Cannot save {path}: {exc.strerror or exc}", severity="error")
            return
        self.notify(f"Saved {path}")

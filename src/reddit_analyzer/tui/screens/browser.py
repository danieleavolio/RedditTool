"""Browser: search the local posts, filter them and read a post with its comments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Select, Static

from reddit_analyzer.models import Comment, Post
from reddit_analyzer.tui.screens.common import ALL, CollectionPicker

if TYPE_CHECKING:
    from reddit_analyzer.tui.app import RpaApp

MAX_COMMENTS = 200


def render_post(post: Post, comments: list[Comment]) -> Text:
    """The preview pane as plain styled text (never parsed as markup: Reddit text has brackets)."""
    out = Text()
    out.append(post.title + "\n", style="bold")
    meta = [
        f"r/{post.subreddit}",
        f"u/{post.author or '[deleted]'}",
        f"score {post.score}",
        f"{post.num_comments} comments",
        post.created_utc.strftime("%Y-%m-%d %H:%M"),
    ]
    out.append(" · ".join(meta) + "\n", style="dim")
    out.append(post.full_url + "\n\n", style="underline blue")
    if post.selftext:
        out.append(post.selftext + "\n")
    elif not post.is_self:
        out.append(post.url + "\n", style="underline blue")
    out.append(f"\n── Comments stored locally: {len(comments)} ──\n", style="bold cyan")
    for comment in comments[:MAX_COMMENTS]:
        pad = "  " * min(comment.depth, 6)
        out.append(f"{pad}u/{comment.author or '[deleted]'} ({comment.score})\n", style="green")
        out.append("".join(f"{pad}{line}\n" for line in comment.body.splitlines() or [""]))
        out.append("\n")
    if len(comments) > MAX_COMMENTS:
        out.append(f"... and {len(comments) - MAX_COMMENTS} more\n", style="dim")
    return out


class BrowserScreen(CollectionPicker):
    app: RpaApp  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._posts: dict[str, Post] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="browser-filters"):
            yield Select(
                [("All collections", ALL)], value=ALL, allow_blank=False, compact=True, id="b-coll"
            )
            yield Input(placeholder="search title and text (Enter)", compact=True, id="b-search")
            yield Input(placeholder="subreddit", compact=True, id="b-sub")
        with Horizontal(id="browser-body"):
            yield DataTable(id="posts", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(id="preview-pane"):
                yield Static("Select a post to read it.", id="preview")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#posts", DataTable).add_columns("Score", "Subreddit", "Date", "Title")

    def on_screen_resume(self) -> None:
        select = self.query_one("#b-coll", Select)
        wanted = self.app.collection or ALL
        rows = self.app.service.overview()
        options = [("All collections", ALL)] + [(f"{c.name} ({c.posts})", c.name) for c in rows]
        self.fill_select(select, options, wanted)
        self.reload()

    @on(Select.Changed, "#b-coll")
    def _collection_changed(self, event: Select.Changed) -> None:
        if self._syncing:
            return
        self.app.collection = str(event.value) or None
        self.reload()

    @on(Input.Submitted)
    def _filters_submitted(self) -> None:
        self.reload()

    def reload(self) -> None:
        collection = str(self.query_one("#b-coll", Select).value) or None
        posts = self.app.service.posts(
            collection,
            text=self.query_one("#b-search", Input).value,
            subreddit=self.query_one("#b-sub", Input).value,
        )
        table = self.query_one("#posts", DataTable)
        table.clear()
        self._posts = {p.id: p for p in posts}
        for post in posts:
            table.add_row(
                str(post.score),
                post.subreddit,
                post.created_utc.strftime("%Y-%m-%d"),
                " ".join(post.title.split())[:120],
                key=post.id,
            )
        self.sub_title = f"{len(posts)} posts"
        if not posts:
            self.query_one("#preview", Static).update("No posts match. Collect some with F2.")

    @on(DataTable.RowHighlighted, "#posts")
    def _highlighted(self, event: DataTable.RowHighlighted) -> None:
        post = self._posts.get(event.row_key.value or "")
        if post is None:
            return
        comments = self.app.service.comments(post.id)
        self.query_one("#preview", Static).update(render_post(post, comments))
        self.query_one("#preview-pane", VerticalScroll).scroll_home(animate=False)

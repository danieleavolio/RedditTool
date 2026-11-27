"""The only bridge between the interfaces (TUI, GUI) and the core.

Every method opens its own ``Database`` connection, so it is safe to call from a UI
worker thread (SQLite connections must not cross threads). Methods that touch the network
or run long (``execute_run``, ``auth_status``) are meant for workers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

import yaml

from reddit_analyzer.cli.collect import slugify
from reddit_analyzer.collect.runner import CancelCheck, ProgressCallback, run_collection
from reddit_analyzer.config import Settings, load_settings
from reddit_analyzer.datasets.builder import BuildResult, Preview, build, preview
from reddit_analyzer.datasets.recipe import Recipe, parse_recipe
from reddit_analyzer.errors import DatasetError
from reddit_analyzer.models import Comment, Post, Run
from reddit_analyzer.sources.base import Source
from reddit_analyzer.sources.oauth import AuthStatus, RedditClient
from reddit_analyzer.stats import CollectionStats, collection_stats
from reddit_analyzer.storage import Database

SourceFactory = Callable[[], Source]

TEMPLATE = """\
name: my-dataset
collection: {collection}
unit: post            # post | comment | pair
# search: "keywords"  # optional local full-text match

filters:
  min_score: 1
  exclude_removed: true
  min_chars: 40

transform:
  strip: [urls, markdown]
  dedup: exact

output:
  format: jsonl       # csv | jsonl | parquet | hf
"""


def find_recipes(root: Path) -> list[Path]:
    folder = root / "recipes"
    return sorted(folder.rglob("*.yaml")) + sorted(folder.rglob("*.yml")) if folder.is_dir() else []


@dataclass(frozen=True)
class CollectionRow:
    name: str
    posts: int
    comments: int
    runs: int


def recipe_from_text(text: str) -> Recipe:
    """Parse and validate YAML typed in the editor. Raises ``DatasetError`` with a readable text."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DatasetError(f"Not valid YAML: {exc}") from exc
    return parse_recipe(data)


class Service:
    def __init__(
        self, settings: Settings | None = None, source_factory: SourceFactory | None = None
    ):
        self.settings = settings or load_settings()
        self._source_factory = source_factory or (lambda: RedditClient.from_config(self.settings))

    def _db(self) -> Database:
        return Database.open(self.settings)

    # -- Reading --------------------------------------------------------------------------

    def overview(self) -> list[CollectionRow]:
        with self._db() as db:
            return [
                CollectionRow(
                    c.name,
                    db.count_posts(c.name),
                    db.count_comments(c.name),
                    len(db.list_runs(collection=c.name)),
                )
                for c in db.list_collections()
            ]

    def recent_runs(self, limit: int = 15) -> list[Run]:
        with self._db() as db:
            return db.list_runs(limit=limit)

    def posts(
        self, collection: str | None, text: str = "", subreddit: str = "", limit: int = 500
    ) -> list[Post]:
        """Posts newest first, or best matches first when ``text`` is given."""
        sub = subreddit.strip().removeprefix("/").removeprefix("r/").lower()
        with self._db() as db:
            if text.strip():
                found = db.search_posts(text, collection, limit=10_000 if sub else limit)
                if sub:
                    found = [p for p in found if p.subreddit.lower() == sub]
                return found[:limit]
            return list(islice(db.iter_posts(collection=collection, subreddit=sub or None), limit))

    def comments(self, post_id: str) -> list[Comment]:
        with self._db() as db:
            return db.get_comments(post_id)

    def stats(self, collection: str | None) -> CollectionStats:
        with self._db() as db:
            return collection_stats(db, collection)

    # -- Collecting -----------------------------------------------------------------------

    @staticmethod
    def default_collection(text: str) -> str:
        return slugify(text)

    def create_run(self, run: Run) -> Run:
        with self._db() as db:
            return db.create_run(run)

    def get_run(self, run_id: int) -> Run | None:
        with self._db() as db:
            return db.get_run(run_id)

    def execute_run(
        self,
        run: Run,
        on_progress: ProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> Run:
        """Run or resume ``run`` to the end. Blocking: call it from a worker thread."""
        source = self._source_factory()  # fails early with the "no credentials" error
        try:
            with self._db() as db:
                return run_collection(db, source, run, on_progress, should_cancel)
        finally:
            close = getattr(source, "close", None)
            if close:
                close()

    def auth_status(self) -> AuthStatus:
        """Check the credentials and the rate limit. Blocking: call it from a worker."""
        with RedditClient.from_config(self.settings) as client:
            return client.check_auth()

    # -- Datasets -------------------------------------------------------------------------

    def preview_recipe(self, text: str, n: int = 30) -> tuple[Recipe, Preview]:
        recipe = recipe_from_text(text)
        with self._db() as db:
            return recipe, preview(recipe, db, n)

    def build_recipe(self, text: str, out: Path | None = None) -> tuple[Recipe, BuildResult]:
        recipe = recipe_from_text(text)
        with self._db() as db:
            return recipe, build(recipe, db, out or Path("out") / recipe.name)

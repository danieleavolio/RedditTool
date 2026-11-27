"""The pipeline: collection -> filters -> text template and cleaning -> filters on the text ->
de-duplication -> split -> exporter. Same recipe + same database = same output.

Rows are produced oldest first, so de-duplication always keeps the earliest copy.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from typing import Any

from reddit_analyzer.datasets.fields import DEFAULT_TEMPLATE, field_types
from reddit_analyzer.datasets.filters import FilterSet
from reddit_analyzer.datasets.recipe import Recipe, recipe_to_yaml
from reddit_analyzer.datasets.split import assign_part
from reddit_analyzer.datasets.transforms import Cleaner, make_deduper
from reddit_analyzer.errors import DatasetError
from reddit_analyzer.export import get_writer
from reddit_analyzer.export.card import render_card
from reddit_analyzer.models import Comment, Post
from reddit_analyzer.storage import Database

Row = dict[str, Any]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Stats:
    """What happened to the rows. ``dropped`` maps a reason to how many rows it removed."""

    seen: int = 0
    kept: int = 0
    dropped: Counter[str] = field(default_factory=Counter)
    parts: Counter[str] = field(default_factory=Counter)
    subreddits: Counter[str] = field(default_factory=Counter)
    chars_total: int = 0
    chars_max: int = 0

    @property
    def chars_mean(self) -> float:
        return self.chars_total / self.kept if self.kept else 0.0


@dataclass(frozen=True)
class Preview:
    rows: list[Row]
    stats: Stats


@dataclass(frozen=True)
class BuildResult:
    files: list[Path]
    card: Path
    stats: Stats


def _post_row(post: Post) -> Row:
    return {
        "id": post.id, "subreddit": post.subreddit, "author": post.author,
        "created_utc": _iso(post.created_utc), "score": post.score,
        "upvote_ratio": post.upvote_ratio, "num_comments": post.num_comments,
        "title": post.title, "selftext": post.selftext, "url": post.url,
        "permalink": post.permalink, "flair": post.flair, "over_18": post.over_18,
        "is_self": post.is_self, "lang": post.lang,
    }  # fmt: skip


def _comment_row(post: Post, comment: Comment) -> Row:
    return {
        "id": comment.id, "post_id": post.id, "subreddit": post.subreddit,
        "parent_id": comment.parent_id, "depth": comment.depth, "author": comment.author,
        "created_utc": _iso(comment.created_utc), "score": comment.score,
        "title": post.title, "body": comment.body,
    }  # fmt: skip


def _pair_row(post: Post, reply: Comment) -> Row:
    row = _post_row(post)
    row = {k: row[k] for k in (
        "id", "subreddit", "author", "created_utc", "score", "num_comments", "title",
        "selftext", "permalink",
    )}  # fmt: skip
    row.update(
        comment_id=reply.id,
        comment_author=reply.author,
        comment_score=reply.score,
        body=reply.body,
    )
    return row


def _reply_order(comment: Comment) -> tuple[int, float, str]:
    """Best reply first: highest score, then earliest, then id (a stable tie-break)."""
    return (-comment.score, comment.created_utc.timestamp(), comment.id)


class _Pipeline:
    def __init__(self, recipe: Recipe, db: Database, stats: Stats):
        self.recipe, self.db, self.stats = recipe, db, stats
        self.filters = FilterSet(recipe.filters)
        self.clean = Cleaner(recipe.transform)
        self.dedup = make_deduper(recipe.transform)
        self.template = recipe.transform.text or DEFAULT_TEMPLATE[recipe.unit]

    def _drop(self, reason: str) -> None:
        self.stats.dropped[reason] += 1

    # -- stage 1: pick candidates and apply the filters that need no text ----------------

    def _candidates(self) -> Iterator[tuple[Row, str | None, Row | None]]:
        """Yield ``(row, known_lang, reply)``; ``reply`` is only set for the pair unit."""
        r, flt, unit = self.recipe, self.filters, self.recipe.unit
        for post in self.db.iter_posts(r.collection, text=r.search, oldest_first=True):
            if unit == "post":
                self.stats.seen += 1
                if reason := flt.post_reason(post):
                    self._drop(reason)
                    continue
                yield _post_row(post), post.lang, None
            elif unit == "comment":
                comments = self.db.get_comments(post.id)
                meta = flt.meta_reason(post)
                for comment in comments:
                    self.stats.seen += 1
                    if reason := meta or flt.comment_reason(comment):
                        self._drop(reason)
                        continue
                    yield _comment_row(post, comment), None, None
            else:
                self.stats.seen += 1
                if reason := flt.post_reason(post):
                    self._drop(reason)
                    continue
                reply = self._best_reply(post)
                if reply is None:
                    self._drop("no_reply")
                    continue
                yield _pair_row(post, reply), post.lang, reply

    def _best_reply(self, post: Post) -> Comment | None:
        usable = [
            c
            for c in self.db.get_comments(post.id)
            if self.filters.status_reason(c.author, c.status) is None
        ]
        for comment in sorted(usable, key=_reply_order):
            if not self.filters.length_reason(self.clean(comment.body)):
                return comment
        return None

    # -- stage 2: text, text filters, dedup, split ---------------------------------------

    def rows(self) -> Iterator[Row]:
        recipe = self.recipe
        for row, known_lang, reply in self._candidates():
            values = {k: ("" if v is None else v) for k, v in row.items()}
            row["text"] = self.clean(self.template.format_map(values))
            if reply is not None:
                row["response"] = self.clean(reply.body)
            reason = self.filters.length_reason(row["text"]) or self.filters.lang_reason(
                row["text"], known_lang
            )
            if reason:
                self._drop(reason)
                continue
            if self.dedup is not None:
                fingerprint = row["text"] + "\n\n" + row.get("response", "")
                if self.dedup.is_duplicate(fingerprint):
                    self._drop(f"duplicate_{recipe.transform.dedup}")
                    continue
            row["part"] = (
                assign_part(row.get("post_id", row["id"]), recipe.split) if recipe.split else ""
            )
            self.stats.kept += 1
            self.stats.parts[row["part"]] += 1
            self.stats.subreddits[row["subreddit"]] += 1
            self.stats.chars_total += len(row["text"])
            self.stats.chars_max = max(self.stats.chars_max, len(row["text"]))
            yield row


def iter_rows(recipe: Recipe, db: Database, stats: Stats | None = None) -> Iterator[Row]:
    """Every row of the dataset, in a stable order. ``stats`` fills up as rows are consumed."""
    return _Pipeline(recipe, db, stats if stats is not None else Stats()).rows()


def preview(recipe: Recipe, db: Database, n: int = 20) -> Preview:
    """The first ``n`` rows plus statistics for the *whole* dataset. Writes nothing."""
    stats = Stats()
    rows = iter_rows(recipe, db, stats)
    head = list(islice(rows, n))
    for _ in rows:  # exhaust the pipeline so the statistics cover everything
        pass
    return Preview(head, stats)


def _paths(recipe: Recipe, out_dir: Path, suffix: str) -> dict[str, Path]:
    parts = list(recipe.split.parts) if recipe.split else [""]
    return {
        p: out_dir / (f"{recipe.name}.{p}{suffix}" if p else f"{recipe.name}{suffix}")
        for p in parts
    }


def build(
    recipe: Recipe, db: Database, out_dir: Path | str, now: datetime | None = None
) -> BuildResult:
    """Write the dataset and its ``dataset_card.md`` into ``out_dir``.

    Data files are byte-for-byte reproducible. Only the card carries a date.
    """
    out = Path(out_dir)
    if db.get_collection(recipe.collection) is None:
        names = ", ".join(c.name for c in db.list_collections()) or "none yet"
        raise DatasetError(
            f"Collection {recipe.collection!r} does not exist. Existing collections: {names}."
        )
    out.mkdir(parents=True, exist_ok=True)
    writer_cls = get_writer(recipe.output.format)
    types = field_types(recipe.unit, recipe.fields)
    paths = _paths(recipe, out, writer_cls.suffix)
    stats = Stats()
    writers = {part: writer_cls(path, types) for part, path in paths.items()}
    try:
        for row in iter_rows(recipe, db, stats):
            writers[row["part"]].write(row)
    except BaseException:
        for w in writers.values():
            w.abort()
        raise
    for w in writers.values():
        w.close()
    card = out / "dataset_card.md"
    card.write_text(
        render_card(
            recipe=recipe,
            recipe_yaml=recipe_to_yaml(recipe),
            stats=stats,
            files=[p.name for p in paths.values()],
            runs=db.list_runs(collection=recipe.collection),
            generated_at=now or datetime.now(UTC),
        ),
        encoding="utf-8",
        newline="\n",
    )
    return BuildResult(list(paths.values()), card, stats)


__all__ = ["BuildResult", "Preview", "Row", "Stats", "build", "iter_rows", "preview"]

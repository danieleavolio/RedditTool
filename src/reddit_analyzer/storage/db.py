"""SQLite storage: posts, comments, runs and collections.

A ``Database`` wraps one connection and is meant to be used from one thread. Background
workers (TUI, GUI) open their own ``Database`` on the same file; WAL mode lets them coexist.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from reddit_analyzer.config import Settings, load_settings
from reddit_analyzer.errors import StorageError
from reddit_analyzer.models import (
    AnalysisResult,
    Collection,
    Comment,
    ContentStatus,
    Post,
    Run,
    RunParams,
    RunStatus,
)
from reddit_analyzer.storage.migrate import apply_migrations

_PARAMS = TypeAdapter(RunParams)
_CHUNK = 500  # stays well under SQLite's bound-variable limit

_POST_FIELDS = (
    "id", "subreddit", "author", "title", "selftext", "url", "permalink", "score",
    "upvote_ratio", "num_comments", "created_utc", "over_18", "is_self", "flair",
    "status", "lang", "raw",
)  # fmt: skip
# Everything a re-fetch may legitimately change. created_utc, first_seen and lang
# (filled by the language analyzer) are never overwritten.
_POST_MUTABLE = (
    "subreddit", "author", "title", "selftext", "url", "permalink", "score", "upvote_ratio",
    "num_comments", "over_18", "is_self", "flair", "status", "raw",
)  # fmt: skip
_COMMENT_MUTABLE = ("parent_id", "depth", "author", "body", "score", "status", "raw")


@dataclass(frozen=True)
class UpsertResult:
    inserted: int
    updated: int


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _epoch(value: float) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _chunks(items: Sequence[str]) -> Iterator[Sequence[str]]:
    for i in range(0, len(items), _CHUNK):
        yield items[i : i + _CHUNK]


def _post_row(post: Post, now: str) -> dict[str, Any]:
    row = post.model_dump(exclude={"raw"})
    row["created_utc"] = post.created_utc.timestamp()
    row["status"] = post.status.value
    row["raw"] = json.dumps(post.raw)
    row["first_seen"] = now
    return row


def _comment_row(comment: Comment) -> dict[str, Any]:
    row = comment.model_dump(exclude={"raw"})
    row["created_utc"] = comment.created_utc.timestamp()
    row["status"] = comment.status.value
    row["raw"] = json.dumps(comment.raw)
    return row


def _to_post(row: sqlite3.Row) -> Post:
    return Post(
        **{k: row[k] for k in _POST_FIELDS if k not in ("created_utc", "status", "raw")},
        created_utc=_epoch(row["created_utc"]),
        status=ContentStatus(row["status"]),
        raw=json.loads(row["raw"]),
    )


def _to_comment(row: sqlite3.Row) -> Comment:
    return Comment(
        id=row["id"],
        post_id=row["post_id"],
        parent_id=row["parent_id"],
        depth=row["depth"],
        author=row["author"],
        body=row["body"],
        score=row["score"],
        created_utc=_epoch(row["created_utc"]),
        status=ContentStatus(row["status"]),
        raw=json.loads(row["raw"]),
    )


def _to_run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        collection=row["collection"],
        source=row["source"],
        params=_PARAMS.validate_json(row["params"]),
        status=RunStatus(row["status"]),
        cursor=row["cursor"],
        posts_fetched=row["posts_fetched"],
        posts_inserted=row["posts_inserted"],
        posts_updated=row["posts_updated"],
        comments_fetched=row["comments_fetched"],
        error=row["error"],
        created_at=_dt(row["created_at"]),
        started_at=_dt(row["started_at"]),
        finished_at=_dt(row["finished_at"]),
    )


def _fts_query(text: str) -> str:
    """Quote every term so user input can never be read as FTS5 syntax (AND semantics)."""
    return " ".join('"' + term.replace('"', '""') + '"' for term in text.split())


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None)  # explicit transactions
        self._conn.row_factory = sqlite3.Row
        self._depth = 0
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.execute("PRAGMA journal_mode = WAL")
            apply_migrations(self._conn)
        except BaseException:
            self._conn.close()
            raise

    @classmethod
    def open(cls, settings: Settings | None = None) -> Database:
        return cls((settings or load_settings()).db_path)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Atomic block. Nested blocks become savepoints, so callers can compose freely."""
        level = self._depth
        savepoint = f"sp{level}"
        self._conn.execute("BEGIN IMMEDIATE" if level == 0 else f"SAVEPOINT {savepoint}")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if level == 0:
                self._conn.execute("ROLLBACK")
            else:
                self._conn.execute(f"ROLLBACK TO {savepoint}")
                self._conn.execute(f"RELEASE {savepoint}")
            raise
        self._depth -= 1
        self._conn.execute("COMMIT" if level == 0 else f"RELEASE {savepoint}")

    # -- Collections --------------------------------------------------------------------

    def ensure_collection(self, name: str, description: str = "") -> Collection:
        """Return the collection, creating it first if needed. Validates the name."""
        collection = Collection(name=name, description=description)
        self._conn.execute(
            "INSERT OR IGNORE INTO collections(name, description, created_at) VALUES (?, ?, ?)",
            (collection.name, collection.description, collection.created_at.isoformat()),
        )
        stored = self.get_collection(name)
        assert stored is not None
        return stored

    def get_collection(self, name: str) -> Collection | None:
        row = self._conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return Collection(
            name=row["name"], description=row["description"], created_at=_dt(row["created_at"])
        )

    def list_collections(self) -> list[Collection]:
        rows = self._conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
        return [
            Collection(
                name=r["name"], description=r["description"], created_at=_dt(r["created_at"])
            )
            for r in rows
        ]

    # -- Runs ---------------------------------------------------------------------------

    def create_run(self, run: Run) -> Run:
        if run.id is not None:
            raise ValueError("create_run needs a run without an id")
        with self.transaction():
            self.ensure_collection(run.collection)
            cur = self._conn.execute(
                "INSERT INTO runs(collection, source, params, status, cursor, posts_fetched,"
                " posts_inserted, posts_updated, comments_fetched, error, created_at,"
                " started_at, finished_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run.collection,
                    run.source,
                    run.params.model_dump_json(),
                    run.status.value,
                    run.cursor,
                    run.posts_fetched,
                    run.posts_inserted,
                    run.posts_updated,
                    run.comments_fetched,
                    run.error,
                    run.created_at.isoformat(),
                    run.started_at.isoformat() if run.started_at else None,
                    run.finished_at.isoformat() if run.finished_at else None,
                ),
            )
        return run.model_copy(update={"id": cur.lastrowid})

    def update_run(self, run: Run) -> None:
        """Persist the mutable state of a run (status, cursor, counters, timestamps)."""
        cur = self._conn.execute(
            "UPDATE runs SET status=?, cursor=?, posts_fetched=?, posts_inserted=?,"
            " posts_updated=?, comments_fetched=?, error=?, started_at=?, finished_at=?"
            " WHERE id=?",
            (
                run.status.value,
                run.cursor,
                run.posts_fetched,
                run.posts_inserted,
                run.posts_updated,
                run.comments_fetched,
                run.error,
                run.started_at.isoformat() if run.started_at else None,
                run.finished_at.isoformat() if run.finished_at else None,
                run.id,
            ),
        )
        if cur.rowcount == 0:
            raise StorageError(f"Run {run.id} does not exist.")

    def get_run(self, run_id: int) -> Run | None:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return _to_run(row) if row else None

    def list_runs(
        self,
        collection: str | None = None,
        status: RunStatus | None = None,
        limit: int | None = None,
    ) -> list[Run]:
        sql, args = "SELECT * FROM runs WHERE 1=1", []
        if collection is not None:
            sql, args = sql + " AND collection = ?", [*args, collection]
        if status is not None:
            sql, args = sql + " AND status = ?", [*args, status.value]
        sql += " ORDER BY id DESC"
        if limit is not None:
            sql, args = sql + " LIMIT ?", [*args, limit]
        return [_to_run(r) for r in self._conn.execute(sql, args)]

    # -- Posts and comments -------------------------------------------------------------

    def _existing(self, table: str, ids: Sequence[str]) -> set[str]:
        found: set[str] = set()
        for chunk in _chunks(ids):
            marks = ",".join("?" * len(chunk))
            rows = self._conn.execute(f"SELECT id FROM {table} WHERE id IN ({marks})", chunk)
            found.update(r["id"] for r in rows)
        return found

    def upsert_posts(self, posts: Iterable[Post], update_existing: bool = True) -> UpsertResult:
        """Insert new posts and refresh known ones. With ``update_existing=False`` known
        posts are left untouched (used when importing older, poorer data)."""
        unique = {p.id: p for p in posts}  # a post repeated in one batch counts once
        if not unique:
            return UpsertResult(0, 0)
        now = _now()
        columns = ", ".join((*_POST_FIELDS, "first_seen", "updated_at"))
        values = ", ".join(f":{c}" for c in (*_POST_FIELDS, "first_seen", "first_seen"))
        if update_existing:
            sets = ", ".join(f"{c}=excluded.{c}" for c in (*_POST_MUTABLE, "updated_at"))
            conflict = f"DO UPDATE SET {sets}"
        else:
            conflict = "DO NOTHING"
        sql = f"INSERT INTO posts ({columns}) VALUES ({values}) ON CONFLICT(id) {conflict}"
        with self.transaction():
            known = self._existing("posts", list(unique))
            self._conn.executemany(sql, [_post_row(p, now) for p in unique.values()])
        updated = len(known) if update_existing else 0
        return UpsertResult(inserted=len(unique) - len(known), updated=updated)

    def upsert_comments(self, comments: Iterable[Comment]) -> UpsertResult:
        unique = {c.id: c for c in comments}
        if not unique:
            return UpsertResult(0, 0)
        columns = ("id", "post_id", "created_utc", *_COMMENT_MUTABLE)
        sets = ", ".join(f"{c}=excluded.{c}" for c in _COMMENT_MUTABLE)
        sql = (
            f"INSERT INTO comments ({', '.join(columns)}) "
            f"VALUES ({', '.join(f':{c}' for c in columns)}) "
            f"ON CONFLICT(id) DO UPDATE SET {sets}"
        )
        with self.transaction():
            known = self._existing("comments", list(unique))
            self._conn.executemany(sql, [_comment_row(c) for c in unique.values()])
        return UpsertResult(inserted=len(unique) - len(known), updated=len(known))

    def link_posts(self, run_id: int, post_ids: Iterable[str]) -> None:
        """Record that ``run_id`` saw these posts. This is what puts a post in a collection."""
        self._conn.executemany(
            "INSERT OR IGNORE INTO run_posts(run_id, post_id) VALUES (?, ?)",
            [(run_id, pid) for pid in post_ids],
        )

    @staticmethod
    def _in_collection(collection: str | None, alias: str = "p") -> tuple[str, list[Any]]:
        if collection is None:
            return "", []
        return (
            f" AND EXISTS (SELECT 1 FROM run_posts rp JOIN runs r ON r.id = rp.run_id"
            f" WHERE rp.post_id = {alias}.id AND r.collection = ?)",
            [collection],
        )

    def get_post(self, post_id: str) -> Post | None:
        row = self._conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return _to_post(row) if row else None

    def iter_posts(
        self,
        collection: str | None = None,
        subreddit: str | None = None,
        text: str | None = None,
        oldest_first: bool = False,
    ) -> Iterator[Post]:
        """Posts, newest first (or oldest first), optionally limited to a collection,
        a subreddit and/or a full-text match on title and selftext (all terms must match)."""
        sql, args = "SELECT p.* FROM posts p WHERE 1=1", []
        clause, extra = self._in_collection(collection)
        sql, args = sql + clause, [*args, *extra]
        if subreddit is not None:
            sql, args = sql + " AND p.subreddit = ? COLLATE NOCASE", [*args, subreddit]
        if text is not None:
            match = _fts_query(text)
            if not match:
                return
            sql += " AND p.rid IN (SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?)"
            args.append(match)
        sql += (
            " ORDER BY p.created_utc, p.id"
            if oldest_first
            else " ORDER BY p.created_utc DESC, p.id"
        )
        for row in self._conn.execute(sql, args):
            yield _to_post(row)

    def count_posts(self, collection: str | None = None) -> int:
        clause, args = self._in_collection(collection)
        row = self._conn.execute(f"SELECT COUNT(*) FROM posts p WHERE 1=1{clause}", args)
        return row.fetchone()[0]

    def search_posts(self, text: str, collection: str | None = None, limit: int = 50) -> list[Post]:
        """Full-text search over title and selftext, best matches first."""
        match = _fts_query(text)
        if not match:
            return []
        clause, extra = self._in_collection(collection)
        rows = self._conn.execute(
            "SELECT p.* FROM posts_fts JOIN posts p ON p.rid = posts_fts.rowid"
            f" WHERE posts_fts MATCH ?{clause} ORDER BY posts_fts.rank LIMIT ?",
            [match, *extra, limit],
        )
        return [_to_post(r) for r in rows]

    def get_comments(self, post_id: str) -> list[Comment]:
        rows = self._conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_utc, id", (post_id,)
        )
        return [_to_comment(r) for r in rows]

    def count_comments(self, collection: str | None = None) -> int:
        clause, args = self._in_collection(collection, alias="c_post")
        row = self._conn.execute(
            "SELECT COUNT(*) FROM comments c JOIN posts c_post ON c_post.id = c.post_id"
            f" WHERE 1=1{clause}",
            args,
        )
        return row.fetchone()[0]

    # -- Analysis results ---------------------------------------------------------------

    def save_analysis(self, result: AnalysisResult) -> None:
        """Store (or replace) the result of an analyzer. ``''`` stands for "all collections"."""
        self._conn.execute(
            "INSERT OR REPLACE INTO analysis_results(collection, analyzer, result, computed_at)"
            " VALUES (?, ?, ?, ?)",
            (
                result.collection or "",
                result.analyzer,
                json.dumps(result.data),
                result.computed_at.isoformat(),
            ),
        )

    def list_analyses(self, collection: str | None = None) -> list[AnalysisResult]:
        rows = self._conn.execute(
            "SELECT * FROM analysis_results WHERE collection = ? ORDER BY analyzer",
            (collection or "",),
        )
        return [
            AnalysisResult(
                analyzer=r["analyzer"],
                collection=r["collection"] or None,
                data=json.loads(r["result"]),
                computed_at=_dt(r["computed_at"]),
            )
            for r in rows
        ]

    def get_analysis(self, analyzer: str, collection: str | None = None) -> AnalysisResult | None:
        return next((a for a in self.list_analyses(collection) if a.analyzer == analyzer), None)

    def set_post_languages(self, languages: dict[str, str]) -> None:
        """Store the detected language (ISO code) of posts, by post id."""
        with self.transaction():
            self._conn.executemany(
                "UPDATE posts SET lang = ? WHERE id = ?",
                [(lang, post_id) for post_id, lang in languages.items()],
            )

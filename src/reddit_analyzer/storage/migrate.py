"""Schema migrations (numbered SQL files + ``PRAGMA user_version``) and the legacy DB import."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING

from reddit_analyzer.errors import StorageError
from reddit_analyzer.models import ContentStatus, Post, Run, RunStatus, SearchParams

if TYPE_CHECKING:
    from reddit_analyzer.storage.db import Database

LEGACY_SOURCE = "legacy-import"
_REDDIT = "https://www.reddit.com"


def _migrations() -> list[tuple[int, str]]:
    folder = resources.files("reddit_analyzer.storage").joinpath("migrations")
    found = []
    for item in folder.iterdir():
        match = re.match(r"^(\d+)_.*\.sql$", item.name)
        if match:
            found.append((int(match.group(1)), item.read_text(encoding="utf-8")))
    return sorted(found)


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Bring the database up to the latest schema. Each migration is all-or-nothing."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    migrations = _migrations()
    latest = migrations[-1][0]
    if current > latest:
        raise StorageError(
            f"This database has schema version {current}, newer than the {latest} this "
            "version of Reddit Post Analyzer understands. Upgrade the tool."
        )
    for version, sql in migrations:
        if version <= current:
            continue
        try:
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;")
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            hint = " Your Python's SQLite lacks FTS5 support." if "fts5" in str(exc) else ""
            raise StorageError(f"Database migration {version} failed: {exc}.{hint}") from exc


# -- Import from the pre-0.2 database (data/reddit_posts.db) ------------------------------


@dataclass(frozen=True)
class LegacyImportResult:
    collections: int  # collections created by this import
    posts_inserted: int  # posts that were not in the database yet
    posts_linked: int  # posts now reachable through the imported collections
    skipped_collections: list[str]  # queries already imported earlier
    skipped_rows: int  # rows without a usable post id


def _slug(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:56].strip("-")
    return f"legacy-{slug or 'query'}"


def _legacy_time(value: str | None) -> datetime:
    # The old schema used CURRENT_TIMESTAMP: "YYYY-MM-DD HH:MM:SS", UTC.
    try:
        return datetime.fromisoformat(value or "").replace(tzinfo=UTC)
    except ValueError:
        return datetime.now(UTC)


def _legacy_post(row: sqlite3.Row, query: str) -> Post | None:
    post_id = row["post_id"]
    if not post_id or post_id == "N/A":
        return None
    link = row["url_post"] or ""
    permalink = link.removeprefix(_REDDIT)
    subreddit = row["categoria"]
    if not subreddit or subreddit == "N/A":
        match = re.match(r"^/r/([^/]+)/", permalink)
        subreddit = match.group(1) if match else "unknown"
    selftext = row["contenuto"] or ""
    status = {"[removed]": ContentStatus.REMOVED, "[deleted]": ContentStatus.DELETED}.get(
        selftext, ContentStatus.OK
    )
    # The old schema never stored the post date, author or comment count. The retrieval
    # time stands in for created_utc: it is NOT the real date, hence the raw marker.
    return Post(
        id=post_id,
        subreddit=subreddit,
        author=None,
        title=row["titolo"] or "",
        selftext=selftext,
        url=link,
        permalink=permalink,
        score=int(row["punteggio"] or 0),
        upvote_ratio=None,
        num_comments=0,
        created_utc=_legacy_time(row["timestamp_retrieval"]),
        over_18=False,
        is_self=bool(selftext),
        flair=None,
        status=status,
        raw={"legacy": True, "query_term": query, "created_utc_is_retrieval_time": True},
    )


def import_legacy(db: Database, legacy_path: Path | str) -> LegacyImportResult:
    """Import the old single-table database: one collection per search query.

    Safe to repeat: queries that were already imported are skipped, and posts that the new
    database already knows (possibly with richer data) are never overwritten.
    """
    path = Path(legacy_path)
    if not path.is_file():
        raise StorageError(f"Legacy database not found: {path}")
    try:
        src = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        src.row_factory = sqlite3.Row
        rows = src.execute(
            "SELECT post_id, query_term, titolo, contenuto, categoria, punteggio, url_post,"
            " timestamp_retrieval FROM posts ORDER BY query_term, rowid"
        ).fetchall()
        src.close()
    except sqlite3.Error as exc:
        raise StorageError(f"{path} is not a legacy Reddit Post Analyzer database: {exc}") from exc

    created, inserted, linked, skipped_rows = 0, 0, 0, 0
    skipped: list[str] = []
    for query, group in groupby(rows, key=lambda r: r["query_term"] or "(unknown)"):
        name = _slug(query)
        group_rows = list(group)
        already = any(
            run.source == LEGACY_SOURCE and getattr(run.params, "query", None) == query
            for run in db.list_runs(collection=name)
        )
        if already:
            skipped.append(name)
            continue
        posts = [p for r in group_rows if (p := _legacy_post(r, query))]
        skipped_rows += len(group_rows) - len(posts)
        if not posts:
            continue
        with db.transaction():
            is_new = db.get_collection(name) is None
            run = db.create_run(
                Run(
                    collection=name,
                    source=LEGACY_SOURCE,
                    params=SearchParams(query=query, limit=len(posts)),
                    status=RunStatus.COMPLETED,
                )
            )
            result = db.upsert_posts(posts, update_existing=False)
            db.link_posts(run.id, [p.id for p in posts])
            now = datetime.now(UTC)
            db.update_run(
                run.model_copy(
                    update={
                        "posts_fetched": len(posts),
                        "posts_inserted": result.inserted,
                        "started_at": now,
                        "finished_at": now,
                    }
                )
            )
        created += is_new
        inserted += result.inserted
        linked += len(posts)
    return LegacyImportResult(created, inserted, linked, skipped, skipped_rows)

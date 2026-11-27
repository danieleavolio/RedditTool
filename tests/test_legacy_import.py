import sqlite3

import pytest
from fakes import make_post

from reddit_analyzer.errors import StorageError
from reddit_analyzer.models import ContentStatus
from reddit_analyzer.storage import Database
from reddit_analyzer.storage.migrate import import_legacy

LEGACY_SCHEMA = """
CREATE TABLE posts (
    post_id TEXT PRIMARY KEY, query_term TEXT NOT NULL, titolo TEXT NOT NULL,
    contenuto TEXT, categoria TEXT, punteggio INTEGER, url_post TEXT,
    timestamp_retrieval DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

ROWS = [
    ("a1", "intelligenza artificiale", "Titolo uno", "testo", "italy", 10,
     "https://www.reddit.com/r/italy/comments/a1/titolo_uno/", "2025-03-04 10:20:30"),
    ("a2", "intelligenza artificiale", "Titolo due", "[removed]", "N/A", 3,
     "https://www.reddit.com/r/italy/comments/a2/titolo_due/", "2025-03-04 10:20:31"),
    ("b1", "Rust & Go!", "Rust post", "", "programming", 7,
     "https://www.reddit.com/r/programming/comments/b1/rust_post/", "2025-03-05 08:00:00"),
    ("N/A", "Rust & Go!", "broken", "", "N/A", 0, "", "2025-03-05 08:00:01"),
]  # fmt: skip


@pytest.fixture
def legacy_db(tmp_path):
    path = tmp_path / "reddit_posts.db"
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY_SCHEMA)
    conn.executemany("INSERT INTO posts VALUES (?,?,?,?,?,?,?,?)", ROWS)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def db(tmp_path):
    with Database(tmp_path / "new.db") as database:
        yield database


def test_import_creates_a_collection_per_query(db, legacy_db):
    result = import_legacy(db, legacy_db)

    assert (result.collections, result.posts_inserted, result.posts_linked) == (2, 3, 3)
    assert result.skipped_rows == 1
    assert [c.name for c in db.list_collections()] == [
        "legacy-intelligenza-artificiale",
        "legacy-rust-go",
    ]
    assert {p.id for p in db.iter_posts("legacy-intelligenza-artificiale")} == {"a1", "a2"}
    (run,) = db.list_runs(collection="legacy-rust-go")
    assert run.status.value == "completed" and run.posts_fetched == 1


def test_imported_posts_are_complete_and_honest_about_dates(db, legacy_db):
    import_legacy(db, legacy_db)
    first, removed = db.get_post("a1"), db.get_post("a2")

    assert first.subreddit == "italy" and first.score == 10 and first.is_self
    assert first.permalink == "/r/italy/comments/a1/titolo_uno/"
    assert first.created_utc.isoformat() == "2025-03-04T10:20:30+00:00"
    assert first.raw["legacy"] is True and first.raw["created_utc_is_retrieval_time"] is True
    assert removed.subreddit == "italy"  # recovered from the permalink when categoria was N/A
    assert removed.status is ContentStatus.REMOVED


def test_import_can_be_repeated(db, legacy_db):
    import_legacy(db, legacy_db)
    again = import_legacy(db, legacy_db)

    assert again.collections == 0 and again.posts_inserted == 0 and again.posts_linked == 0
    assert sorted(again.skipped_collections) == [
        "legacy-intelligenza-artificiale",
        "legacy-rust-go",
    ]
    assert db.count_posts() == 3
    assert len(db.list_runs()) == 2


def test_import_never_overwrites_richer_existing_data(db, legacy_db):
    db.upsert_posts([make_post(1, id="a1", title="Real title", score=999, author="someone")])
    result = import_legacy(db, legacy_db)

    assert result.posts_inserted == 2  # a1 already existed
    kept = db.get_post("a1")
    assert (kept.title, kept.score, kept.author) == ("Real title", 999, "someone")
    assert "a1" in {p.id for p in db.iter_posts("legacy-intelligenza-artificiale")}  # still linked


def test_import_errors_are_readable(db, tmp_path):
    with pytest.raises(StorageError, match="not found"):
        import_legacy(db, tmp_path / "missing.db")
    other = tmp_path / "other.db"
    sqlite3.connect(other).execute("CREATE TABLE unrelated (x)").connection.close()
    with pytest.raises(StorageError, match="not a legacy"):
        import_legacy(db, other)

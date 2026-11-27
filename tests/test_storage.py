import sqlite3

import pytest
from fakes import make_comment, make_post
from pydantic import ValidationError

from reddit_analyzer.errors import StorageError
from reddit_analyzer.models import ListingParams, Post, Run, RunStatus, SearchParams
from reddit_analyzer.storage import Database
from reddit_analyzer.storage.migrate import _migrations


@pytest.fixture
def db():
    with Database(":memory:") as database:
        yield database


def _run(collection: str, **kw) -> Run:
    return Run(collection=collection, params=SearchParams(query="rust", limit=10), **kw)


def test_migrations_are_applied_once(tmp_path):
    path = tmp_path / "sub" / "reddit.db"  # parent folder is created
    Database(path).close()
    with Database(path) as db:
        version = db._conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == _migrations()[-1][0]


def test_database_from_the_future_is_refused(tmp_path):
    path = tmp_path / "reddit.db"
    Database(path).close()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 999")
    conn.close()
    with pytest.raises(StorageError, match="newer"):
        Database(path)


def test_upsert_counts_and_refreshes(db):
    first = db.upsert_posts([make_post(1, score=5), make_post(2)])
    assert (first.inserted, first.updated) == (2, 0)

    again = db.upsert_posts([make_post(1, score=50, num_comments=99), make_post(3)])
    assert (again.inserted, again.updated) == (1, 1)
    refreshed = db.get_post("p0001")
    assert (refreshed.score, refreshed.num_comments) == (50, 99)
    assert db.count_posts() == 3


def test_upsert_counts_a_repeated_post_once(db):
    result = db.upsert_posts([make_post(1, score=1), make_post(1, score=2)])
    assert (result.inserted, result.updated) == (1, 0)
    assert db.get_post("p0001").score == 2  # last one wins


def test_upsert_keeps_lang_and_creation_date(db):
    db.upsert_posts([make_post(1)])
    db._conn.execute("UPDATE posts SET lang = 'it' WHERE id = 'p0001'")
    db.upsert_posts([make_post(1, score=7, created_utc=1)])
    post = db.get_post("p0001")
    assert post.lang == "it"
    assert post.created_utc.timestamp() == 1767225601


def test_update_existing_false_leaves_known_posts_alone(db):
    db.upsert_posts([make_post(1, score=50)])
    result = db.upsert_posts([make_post(1, score=1), make_post(2)], update_existing=False)
    assert (result.inserted, result.updated) == (1, 0)
    assert db.get_post("p0001").score == 50


def test_post_roundtrip_keeps_everything(db, load_fixture):
    children = load_fixture("listing_search.json")["data"]["children"]
    posts = [Post.from_reddit(c["data"]) for c in children]
    db.upsert_posts(posts)
    for post in posts:
        assert db.get_post(post.id) == post


def test_same_post_in_two_collections(db):
    run_a = db.create_run(_run("alpha"))
    run_b = db.create_run(_run("beta"))
    shared, only_b = make_post(1), make_post(2)
    db.upsert_posts([shared])
    db.link_posts(run_a.id, [shared.id])
    db.upsert_posts([shared, only_b])
    db.link_posts(run_b.id, [shared.id, only_b.id])

    assert [p.id for p in db.iter_posts(collection="alpha")] == ["p0001"]
    assert {p.id for p in db.iter_posts(collection="beta")} == {"p0001", "p0002"}
    assert db.count_posts("alpha") == 1
    assert db.count_posts() == 2  # one row per post, however many collections


def test_iter_posts_filters_by_subreddit_case_insensitively(db):
    db.upsert_posts([make_post(1, subreddit="Italy"), make_post(2, subreddit="python")])
    assert [p.id for p in db.iter_posts(subreddit="italy")] == ["p0001"]


def test_full_text_search(db):
    db.upsert_posts(
        [
            make_post(1, title="Come imparare Rust", selftext="consigli su Perché partire"),
            make_post(2, title="Python tips"),
        ]
    )
    assert [p.id for p in db.search_posts("rust")] == ["p0001"]
    assert [p.id for p in db.search_posts("perche")] == ["p0001"]  # accent-insensitive
    assert db.search_posts('AND OR "unbalanced (') == []  # input is never FTS syntax
    assert db.search_posts("   ") == []

    db.upsert_posts([make_post(1, title="Tutto su Go")])  # an edited title is re-indexed
    assert db.search_posts("rust") == []
    assert [p.id for p in db.search_posts("go")] == ["p0001"]


def test_search_is_limited_to_a_collection(db):
    run = db.create_run(_run("alpha"))
    db.upsert_posts([make_post(1, title="rust one"), make_post(2, title="rust two")])
    db.link_posts(run.id, ["p0001"])
    assert [p.id for p in db.search_posts("rust", collection="alpha")] == ["p0001"]


def test_comments(db):
    db.upsert_posts([make_post(1), make_post(2)])
    first = db.upsert_comments([make_comment(1, 0), make_comment(1, 1), make_comment(2, 0)])
    assert (first.inserted, first.updated) == (3, 0)
    second = db.upsert_comments([make_comment(1, 0, score=99)])
    assert (second.inserted, second.updated) == (0, 1)
    comments = db.get_comments("p0001")
    assert [c.id for c in comments] == ["c0001_0", "c0001_1"]
    assert comments[0].score == 99
    assert db.count_comments() == 3


def test_comments_need_their_post(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_comments([make_comment(9, 0)])


def test_deleting_a_post_removes_its_comments_and_search_entry(db):
    db.upsert_posts([make_post(1, title="unique-word")])
    db.upsert_comments([make_comment(1, 0)])
    db._conn.execute("DELETE FROM posts WHERE id = 'p0001'")
    assert db.get_comments("p0001") == []
    assert db.search_posts("unique-word") == []


def test_transaction_rolls_back_on_error(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.upsert_posts([make_post(1)])
            raise RuntimeError("boom")
    assert db.count_posts() == 0


def test_nested_transaction_rolls_back_only_the_inner_part(db):
    with db.transaction():
        db.upsert_posts([make_post(1)])
        with pytest.raises(RuntimeError):
            with db.transaction():
                db.upsert_posts([make_post(2)])
                raise RuntimeError("inner")
    assert [p.id for p in db.iter_posts()] == ["p0001"]


def test_run_roundtrip_and_update(db):
    created = db.create_run(
        Run(
            collection="italy-new",
            params=ListingParams(subreddit="italy", sort="top", time="week", limit=300),
        )
    )
    assert created.id == 1
    assert db.get_collection("italy-new") is not None
    loaded = db.get_run(created.id)
    assert loaded == created

    db.update_run(
        created.model_copy(
            update={
                "status": RunStatus.FAILED,
                "cursor": "t3_zzz",
                "posts_fetched": 40,
                "error": "x",
            }
        )
    )
    loaded = db.get_run(created.id)
    assert (loaded.status, loaded.cursor, loaded.posts_fetched, loaded.error) == (
        RunStatus.FAILED,
        "t3_zzz",
        40,
        "x",
    )


def test_list_runs_filters_newest_first(db):
    one = db.create_run(_run("a"))
    two = db.create_run(_run("b"))
    db.update_run(two.model_copy(update={"status": RunStatus.COMPLETED}))
    assert [r.id for r in db.list_runs()] == [two.id, one.id]
    assert [r.id for r in db.list_runs(collection="a")] == [one.id]
    assert [r.id for r in db.list_runs(status=RunStatus.COMPLETED)] == [two.id]
    assert len(db.list_runs(limit=1)) == 1


def test_update_missing_run_fails(db):
    with pytest.raises(StorageError):
        db.update_run(_run("a").model_copy(update={"id": 42}))


def test_invalid_collection_name_is_rejected(db):
    with pytest.raises(ValidationError):
        db.ensure_collection("Not Valid!")


def test_ensure_collection_keeps_the_first_description(db):
    db.ensure_collection("alpha", "original")
    assert db.ensure_collection("alpha", "other").description == "original"
    assert [c.name for c in db.list_collections()] == ["alpha"]

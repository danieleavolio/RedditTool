import csv
import random
from datetime import UTC, datetime

import pytest
from fakes import make_comment, make_post

from reddit_analyzer.datasets.builder import build, iter_rows, preview
from reddit_analyzer.datasets.recipe import parse_recipe
from reddit_analyzer.errors import DatasetError
from reddit_analyzer.models import Run, SearchParams
from reddit_analyzer.storage import Database

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)


def _recipe(**extra):
    return parse_recipe({"name": "demo", "collection": "c", **extra})


def _fill(db: Database, posts, comments=(), collection="c"):
    run = db.create_run(Run(collection=collection, params=SearchParams(query="python")))
    db.upsert_posts(posts)
    db.link_posts(run.id, [p.id for p in posts])
    db.upsert_comments(comments)


@pytest.fixture
def db():
    with Database(":memory:") as database:
        posts = [
            make_post(
                1, score=50, title="Rust is fast", selftext="Visit https://rust-lang.org now"
            ),
            make_post(2, score=2, title="Low score"),
            make_post(3, score=30, title="Removed", selftext="[removed]"),
            make_post(4, score=40, title="Bot post", author="AutoModerator"),
            make_post(5, score=60, title="Adult", over_18=True),
            make_post(6, score=70, title="Other sub", subreddit="rust"),
            make_post(
                7, score=80, title="rust IS fast", selftext="Visit https://rust-lang.org now"
            ),
            make_post(8, score=90, title="Old post", created_utc=1600000000),
        ]
        comments = [
            make_comment(1, 0, score=3, body="meh"),
            make_comment(1, 1, score=9, body="Great **post** u/someone!"),
            make_comment(1, 2, score=20, author="AutoModerator", body="bot says hi"),
            make_comment(1, 3, score=15, body="[removed]"),
            make_comment(7, 0, score=1, body="short"),
        ]
        _fill(database, posts, comments)
        yield database


def _ids(recipe, db):
    return [r["id"] for r in iter_rows(recipe, db)]


def test_post_unit_filters_and_reports_why(db):
    r = _recipe(
        filters={
            "min_score": 10,
            "after": "2026-01-01",
            "subreddits": ["python"],
            "nsfw": "exclude",
            "exclude_bots": True,
        }
    )
    p = preview(r, db)
    assert [row["id"] for row in p.rows] == ["p0001", "p0007"]  # oldest first
    assert p.stats.seen == 8 and p.stats.kept == 2
    assert dict(p.stats.dropped) == {
        "score": 1, "removed": 1, "bot": 1, "nsfw": 1, "subreddit": 1, "date": 1
    }  # fmt: skip
    assert sum(p.stats.dropped.values()) + p.stats.kept == p.stats.seen


def test_removed_are_kept_when_asked(db):
    assert "p0003" in _ids(_recipe(filters={"exclude_removed": False}), db)
    assert "p0003" not in _ids(_recipe(), db)


def test_template_cleaning_text_filters_and_dedup(db):
    r = _recipe(
        filters={"min_score": 10, "min_chars": 5, "subreddits": "python"},
        transform={"text": "{title} ({score}): {selftext}", "strip": ["urls"], "dedup": "exact"},
    )
    rows = list(iter_rows(r, db))
    assert {x["id"]: x["text"] for x in rows}["p0001"] == "Rust is fast (50): Visit now"
    # the score is part of the template, so p0007 is not a duplicate of p0001 here
    assert "p0007" in [x["id"] for x in rows]

    r = _recipe(
        filters={"min_score": 10, "subreddits": "python"},
        transform={"text": "{title}\n{selftext}", "strip": ["urls"], "dedup": "exact"},
    )
    p = preview(r, db)
    assert [x["id"] for x in p.rows if x["id"] in ("p0001", "p0007")] == ["p0001"]
    assert p.stats.dropped["duplicate_exact"] == 1


def test_min_chars_applies_to_cleaned_text(db):
    r = _recipe(
        filters={"min_score": 45, "min_chars": 20, "subreddits": "python"},
        transform={"text": "{selftext}", "strip": ["urls"]},
    )
    p = preview(r, db)
    assert p.stats.dropped["short"] >= 1 and p.rows == []


def test_search_uses_the_local_index(db):
    assert _ids(_recipe(search="rust"), db) == ["p0001", "p0007"]  # case-insensitive
    assert _ids(_recipe(search="rust fast", filters={"min_score": 60}), db) == ["p0007"]
    assert _ids(_recipe(search="nonexistentword"), db) == []


def test_comment_unit(db):
    r = _recipe(unit="comment", filters={"exclude_bots": True, "min_score": 2})
    rows = list(iter_rows(r, db))
    assert [x["id"] for x in rows] == ["c0001_0", "c0001_1"]
    assert rows[1]["text"] == "Great **post** u/someone!"
    assert rows[1]["post_id"] == "p0001" and rows[1]["subreddit"] == "python"
    r = _recipe(unit="comment", transform={"strip": ["markdown", "usernames"]})
    assert [x["text"] for x in iter_rows(r, db)][1] == "Great post !"
    # comment filters see the post's subreddit
    r = _recipe(unit="comment", filters={"subreddits": "rust"})
    assert _ids(r, db) == []


def test_pair_unit_picks_the_best_usable_reply(db):
    r = _recipe(unit="pair", filters={"exclude_bots": True, "min_score": 40})
    rows = list(iter_rows(r, db))
    # p0001: best usable reply skips the bot (20) and the removed one (15) -> score 9
    first = next(x for x in rows if x["id"] == "p0001")
    assert first["comment_id"] == "c0001_1" and first["comment_score"] == 9
    assert first["text"].startswith("Rust is fast")
    assert first["response"] == "Great **post** u/someone!"
    # posts without any usable reply are dropped and counted
    assert "p0002" not in [x["id"] for x in rows]
    assert preview(r, db).stats.dropped["no_reply"] >= 1


def test_pair_skips_replies_that_are_too_short_after_cleaning(db):
    r = _recipe(unit="pair", filters={"min_chars": 6, "min_score": 40, "exclude_bots": True})
    reply = next(x for x in iter_rows(r, db) if x["id"] == "p0001")
    assert reply["comment_id"] == "c0001_1"  # "meh" (3 chars) never wins


def test_split_keeps_a_thread_together(db):
    posts = [make_post(100 + i) for i in range(60)]
    comments = [make_comment(100 + i, k) for i in range(60) for k in range(3)]
    _fill(db, posts, comments, collection="big")
    r = _recipe(
        collection="big",
        unit="comment",
        split={"parts": {"train": 0.7, "dev": 0.3}, "seed": 1},
    )
    part_of = {}
    for row in iter_rows(r, db):
        assert part_of.setdefault(row["post_id"], row["part"]) == row["part"]
    assert set(part_of.values()) == {"train", "dev"}
    post_rows = list(iter_rows(_recipe(collection="big", split=r.split), db))
    assert {x["id"]: x["part"] for x in post_rows} == part_of


def test_lang_filter_prefers_the_stored_language(db):
    """A stored language is trusted, so no detector is needed (langdetect may be absent)."""
    db._conn.execute("UPDATE posts SET lang = 'it' WHERE id IN ('p0001', 'p0002')")
    db._conn.execute("UPDATE posts SET lang = 'en' WHERE id NOT IN ('p0001', 'p0002')")
    assert _ids(_recipe(filters={"lang": "IT"}), db) == ["p0001", "p0002"]


def test_lang_detection_fallback():
    pytest.importorskip("langdetect")
    with Database(":memory:") as db:
        _fill(
            db,
            [
                make_post(
                    1, selftext="Questa è una discussione molto interessante sulla politica."
                ),
                make_post(2, selftext="This is a really interesting discussion about politics."),
            ],
        )
        r = _recipe(filters={"lang": ["it"]}, transform={"text": "{selftext}"})
        assert _ids(r, db) == ["p0001"]


# -- build, output files and determinism -------------------------------------------------


@pytest.mark.parametrize("fmt", ["csv", "jsonl", "parquet"])
def test_same_recipe_same_db_gives_identical_bytes(tmp_path, fmt):
    if fmt == "parquet":
        pytest.importorskip("pyarrow")
    rng = random.Random(3)
    posts = [make_post(i, score=i, selftext=f"body {i} è così") for i in range(1, 80)]
    comments = [make_comment(i, 0) for i in range(1, 80)]
    recipe = _recipe(
        split={"parts": {"a": 0.6, "b": 0.4}, "seed": 5},
        transform={"dedup": "near", "strip": ["markdown"]},
        output={"format": fmt, "fields": ["id", "created_utc", "score", "text"]},
    )
    outputs = []
    for run, order in enumerate(("fwd", "shuffled")):
        with Database(":memory:") as db:
            ordered_posts = list(posts)
            if order == "shuffled":  # insertion order must not matter
                rng.shuffle(ordered_posts)
            _fill(db, ordered_posts, comments)
            out = tmp_path / f"run{run}"
            result = build(recipe, db, out, now=NOW)
        outputs.append({p.name: p.read_bytes() for p in result.files})
    assert outputs[0] == outputs[1]
    assert set(outputs[0]) == {f"demo.a.{fmt}", f"demo.b.{fmt}"}
    assert all(outputs[0].values())


def test_build_writes_card_and_unsplit_file(db, tmp_path):
    recipe = _recipe(filters={"min_score": 10, "subreddits": "python"}, output={"format": "csv"})
    result = build(recipe, db, tmp_path / "out", now=NOW)
    assert [p.name for p in result.files] == ["demo.csv"]
    with open(tmp_path / "out" / "demo.csv", encoding="utf-8", newline="") as f:
        table = list(csv.reader(f))
    assert table[0] == ["id", "subreddit", "created_utc", "score", "num_comments", "text"]
    assert len(table) - 1 == result.stats.kept == 5  # 8 posts - low score - removed - other sub
    card = result.card.read_text(encoding="utf-8")
    assert "Generated on 2026-11-27" in card
    assert "Collection `c`" in card and "search “python”" in card
    assert "not designed or intended for training" in card
    assert "min_score: 10" in card and "`demo.csv`" in card


def test_unknown_collection_is_a_clear_error(db, tmp_path):
    with pytest.raises(DatasetError, match=r"'nope' does not exist.*Existing collections: c"):
        build(_recipe(collection="nope"), db, tmp_path)


def test_failed_build_leaves_no_partial_files(db, tmp_path, monkeypatch):
    from reddit_analyzer.datasets import builder

    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(builder, "assign_part", boom)
    recipe = _recipe(split={"parts": {"a": 0.5, "b": 0.5}})
    with pytest.raises(RuntimeError):
        build(recipe, db, tmp_path / "out")
    assert not list((tmp_path / "out").glob("demo.*"))

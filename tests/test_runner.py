import pytest
from fakes import FakeSource

from reddit_analyzer.collect.runner import run_collection
from reddit_analyzer.errors import ServerError, StorageError
from reddit_analyzer.models import CommentsSpec, Run, RunStatus, SearchParams
from reddit_analyzer.storage import Database


@pytest.fixture
def db(tmp_path):
    with Database(tmp_path / "reddit.db") as database:
        yield database


def _new_run(db, collection="rust", limit=25, comments=False) -> Run:
    params = SearchParams(
        query="rust",
        limit=limit,
        comments=CommentsSpec(depth=1, max_per_post=5) if comments else None,
    )
    return db.create_run(Run(collection=collection, params=params))


def test_full_run(db):
    run = _new_run(db)
    final = run_collection(db, FakeSource(total=25), run)

    assert final.status is RunStatus.COMPLETED
    assert (final.posts_fetched, final.posts_inserted, final.posts_updated) == (25, 25, 0)
    assert final.finished_at is not None and final.error is None
    assert db.count_posts("rust") == 25
    assert db.get_run(run.id) == final


def test_failed_run_keeps_progress_and_resumes_without_double_counting(db):
    run = _new_run(db)
    source = FakeSource(total=25, fail_on_page_call=3)
    with pytest.raises(ServerError):
        run_collection(db, source, run)

    failed = db.get_run(run.id)
    assert failed.status is RunStatus.FAILED
    assert "simulated outage" in failed.error
    assert failed.posts_fetched == 20 and failed.cursor == "20"  # two pages were saved
    assert db.count_posts("rust") == 20

    final = run_collection(db, FakeSource(total=25), failed)
    assert final.status is RunStatus.COMPLETED and final.error is None
    assert (final.posts_fetched, final.posts_inserted, final.posts_updated) == (25, 25, 0)
    assert db.count_posts("rust") == 25


def test_resume_survives_closing_the_database(tmp_path):
    path = tmp_path / "reddit.db"
    with Database(path) as db:
        run = _new_run(db)
        with pytest.raises(ServerError):
            run_collection(db, FakeSource(total=25, fail_on_page_call=2), run)
    # a new process: fresh connection, fresh source
    with Database(path) as db:
        resumed = run_collection(db, FakeSource(total=25), db.get_run(run.id))
        assert resumed.status is RunStatus.COMPLETED
        assert db.count_posts("rust") == 25


def test_ctrl_c_marks_the_run_cancelled_and_reraises(db):
    class Interrupted(FakeSource):
        def iter_pages(self, *args, **kwargs):
            for i, page in enumerate(super().iter_pages(*args, **kwargs)):
                if i == 1:
                    raise KeyboardInterrupt
                yield page

    run = _new_run(db)
    with pytest.raises(KeyboardInterrupt):
        run_collection(db, Interrupted(total=25), run)
    cancelled = db.get_run(run.id)
    assert cancelled.status is RunStatus.CANCELLED and cancelled.posts_fetched == 10

    final = run_collection(db, FakeSource(total=25), cancelled)
    assert final.status is RunStatus.COMPLETED and db.count_posts("rust") == 25


def test_should_cancel_stops_between_pages(db):
    calls = []

    def stop_after_first_page() -> bool:
        calls.append(1)
        return len(calls) > 1

    run = _new_run(db)
    final = run_collection(db, FakeSource(total=25), run, should_cancel=stop_after_first_page)
    assert final.status is RunStatus.CANCELLED
    assert final.posts_fetched == 10 and final.cursor == "10"


def test_completed_run_is_not_executed_again(db):
    run = _new_run(db)
    run_collection(db, FakeSource(total=25), run)
    source = FakeSource(total=25)
    again = run_collection(db, source, run)
    assert again.status is RunStatus.COMPLETED and source.page_calls == 0


def test_run_must_be_saved_first(db):
    unsaved = Run(collection="x", params=SearchParams(query="q"))
    with pytest.raises(ValueError):
        run_collection(db, FakeSource(), unsaved)
    with pytest.raises(StorageError):
        run_collection(db, FakeSource(), unsaved.model_copy(update={"id": 99}))


def test_same_post_in_two_collections(db):
    run_collection(db, FakeSource(total=5), _new_run(db, "alpha", limit=5))
    second = run_collection(db, FakeSource(total=5), _new_run(db, "beta", limit=5))

    assert db.count_posts() == 5  # stored once
    assert db.count_posts("alpha") == 5 and db.count_posts("beta") == 5
    assert second.posts_inserted == 0 and second.posts_updated == 5  # the old bug lost these


def test_comments_are_stored(db):
    final = run_collection(
        db, FakeSource(total=5, comments_per_post=3), _new_run(db, limit=5, comments=True)
    )
    assert final.comments_fetched == 15
    assert db.count_comments("rust") == 15
    assert len(db.get_comments("p0002")) == 3


def test_a_page_is_atomic_when_comments_fail(db):
    run = _new_run(db, limit=25, comments=True)
    source = FakeSource(total=25, fail_comments_for=14)  # page 2 holds posts 10..19
    with pytest.raises(ServerError):
        run_collection(db, source, run)

    failed = db.get_run(run.id)
    assert failed.status is RunStatus.FAILED
    assert failed.posts_fetched == 10 and failed.cursor == "10"
    assert db.count_posts() == 10  # nothing of the failed page leaked in
    assert db.count_comments() == 20

    final = run_collection(db, FakeSource(total=25), failed)
    assert final.posts_fetched == 25 and final.comments_fetched == 50
    assert db.count_posts() == 25 and db.count_comments() == 50


def test_progress_events(db):
    events = []
    run_collection(db, FakeSource(total=25), _new_run(db), on_progress=events.append)
    assert [e.page for e in events] == [1, 2, 3]
    assert [e.run.posts_fetched for e in events] == [10, 20, 25]
    assert [e.end_reason for e in events] == [None, None, "limit"]
    assert all(e.stage == "posts" for e in events)


def test_progress_reports_comment_stage(db):
    events = []
    run = _new_run(db, limit=3, comments=True)
    run_collection(db, FakeSource(total=3), run, on_progress=events.append)
    assert [e.stage for e in events] == ["comments"] * 3 + ["posts"]
    assert [e.post_id for e in events[:3]] == ["p0000", "p0001", "p0002"]

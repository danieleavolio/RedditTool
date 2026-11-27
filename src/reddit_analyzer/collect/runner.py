"""Run a collection job: fetch pages from a source, store them, and stay resumable.

Each page is written in one transaction together with the run's cursor and counters, so a
run killed at any moment resumes from the last fully saved page without losing or counting
anything twice.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from reddit_analyzer.errors import StorageError
from reddit_analyzer.models import Comment, Run, RunStatus
from reddit_analyzer.sources.base import EndReason, Source
from reddit_analyzer.storage import Database


@dataclass(frozen=True)
class Progress:
    """Emitted after every saved page ("posts") and after fetching each post's comments."""

    run: Run  # snapshot of the saved state (cursor and counters)
    page: int  # 1-based page number within this execution
    stage: Literal["posts", "comments"]
    end_reason: EndReason | None = None  # set on the last page; "cap" = Reddit's ~1000 ceiling
    post_id: str | None = None  # the post whose comments were just fetched


ProgressCallback = Callable[[Progress], None]
CancelCheck = Callable[[], bool]


class _Cancelled(Exception):
    pass


def _finish(db: Database, run_id: int, status: RunStatus, error: str | None = None) -> Run:
    run = db.get_run(run_id)
    assert run is not None
    run = run.model_copy(
        update={"status": status, "error": error, "finished_at": datetime.now(UTC)}
    )
    db.update_run(run)
    return run


def run_collection(
    db: Database,
    source: Source,
    run: Run,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> Run:
    """Execute (or resume) a run that already exists in the database and return its final state.

    ``should_cancel`` is polled between pages and between posts; when it returns True the
    run ends as ``cancelled``. Errors end it as ``failed`` and are re-raised; Ctrl+C ends it
    as ``cancelled`` and is re-raised. In every case ``rpa runs resume`` can continue it.
    """
    if run.id is None:
        raise ValueError("run_collection needs a run saved with Database.create_run")
    stored = db.get_run(run.id)
    if stored is None:
        raise StorageError(f"Run {run.id} does not exist.")
    if stored.status is RunStatus.COMPLETED:
        return stored

    stored = stored.model_copy(
        update={
            "status": RunStatus.RUNNING,
            "error": None,
            "finished_at": None,
            "started_at": stored.started_at or datetime.now(UTC),
        }
    )
    db.update_run(stored)
    try:
        _collect(db, source, stored, on_progress, should_cancel)
    except _Cancelled:
        return _finish(db, run.id, RunStatus.CANCELLED)
    except KeyboardInterrupt:
        _finish(db, run.id, RunStatus.CANCELLED)
        raise
    except Exception as exc:
        _finish(db, run.id, RunStatus.FAILED, str(exc) or type(exc).__name__)
        raise
    return _finish(db, run.id, RunStatus.COMPLETED)


def _collect(
    db: Database,
    source: Source,
    run: Run,
    on_progress: ProgressCallback | None,
    should_cancel: CancelCheck | None,
) -> None:
    params = run.params
    assert run.id is not None

    def cancelled() -> bool:
        return bool(should_cancel and should_cancel())

    page_no = 0
    for page in source.iter_pages(params, after=run.cursor, fetched=run.posts_fetched):
        page_no += 1
        if cancelled():
            raise _Cancelled
        # Comments are fetched before anything is written, so the page stays atomic.
        comments: list[Comment] = []
        if params.comments is not None:
            for post in page.posts:
                if cancelled():
                    raise _Cancelled
                comments.extend(source.iter_comments(post.id, params.comments))
                if on_progress:
                    on_progress(Progress(run, page_no, "comments", post_id=post.id))

        with db.transaction():
            posts_result = db.upsert_posts(page.posts)
            db.link_posts(run.id, [p.id for p in page.posts])
            db.upsert_comments(comments)
            run = run.model_copy(
                update={
                    "cursor": page.after,
                    "posts_fetched": run.posts_fetched + len(page.posts),
                    "posts_inserted": run.posts_inserted + posts_result.inserted,
                    "posts_updated": run.posts_updated + posts_result.updated,
                    "comments_fetched": run.comments_fetched + len(comments),
                }
            )
            db.update_run(run)
        if on_progress:
            on_progress(Progress(run, page_no, "posts", end_reason=page.end_reason))

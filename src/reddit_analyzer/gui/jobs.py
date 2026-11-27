"""Run collections in background threads so the web UI never blocks.

No Streamlit here: the manager is a plain object the pages poll. One run at a time, because
parallel runs would only fight for the same Reddit rate limit.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from reddit_analyzer.cli.collect import CAP_NOTE
from reddit_analyzer.collect.runner import Progress
from reddit_analyzer.models import Run
from reddit_analyzer.service import Service


@dataclass
class Job:
    run: Run  # latest saved state, updated on every page
    log: list[str] = field(default_factory=list)
    status_line: str = ""
    final: Run | None = None
    error: str | None = None
    done: bool = False
    cancel: threading.Event = field(default_factory=threading.Event)


class RunManager:
    def __init__(self, service: Service):
        self._service = service
        self._lock = threading.Lock()
        self._job: Job | None = None

    @property
    def job(self) -> Job | None:
        """The running job, or the last finished one (kept so the page can show the result)."""
        return self._job

    @property
    def busy(self) -> bool:
        return self._job is not None and not self._job.done

    def start(self, run: Run, resumed: bool = False) -> Job:
        """Execute ``run`` (already saved in the database) in a thread. Raises if one is running."""
        with self._lock:
            if self.busy:
                raise RuntimeError("A collection is already running.")
            verb = "Resuming" if resumed else "Starting"
            job = Job(run, log=[f"{verb} run {run.id} in collection {run.collection!r}"])
            self._job = job
        threading.Thread(target=self._work, args=(job,), daemon=True, name="rpa-run").start()
        return job

    def cancel(self) -> None:
        if self._job is not None and not self._job.done:
            self._job.cancel.set()

    def _work(self, job: Job) -> None:
        def progress(event: Progress) -> None:
            job.run = event.run
            if event.stage == "comments":
                job.status_line = f"comments of post {event.post_id} ..."
                return
            job.status_line = ""
            run = event.run
            job.log.append(
                f"page {event.page}: {run.posts_fetched} posts "
                f"({run.posts_inserted} new, {run.posts_updated} updated), "
                f"{run.comments_fetched} comments"
            )
            if event.end_reason == "cap":
                job.log.append(CAP_NOTE)

        try:
            final = self._service.execute_run(job.run, progress, job.cancel.is_set)
        except Exception as exc:  # a thread must never die silently: show it in the page
            job.error = str(exc)
            job.log.append(f"Error: {exc}")
            job.log.append(f"Continue later from this page or with: rpa runs resume {job.run.id}")
        else:
            job.final = final
            job.run = final
            job.log.append(
                f"Run {final.id} {final.status.value}: {final.posts_fetched} posts "
                f"({final.posts_inserted} new), {final.comments_fetched} comments."
            )
        finally:
            job.done = True

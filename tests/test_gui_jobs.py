"""RunManager: background runs for the web UI (no Streamlit needed)."""

import threading
import time

import pytest
from fakes import FakeSource

from reddit_analyzer.config import load_settings
from reddit_analyzer.gui.jobs import RunManager
from reddit_analyzer.models import RunStatus, SearchParams
from reddit_analyzer.service import Service
from reddit_analyzer.storage import Database


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_DATA_DIR", str(tmp_path / "data"))
    return load_settings()


def make_manager(settings, source):
    return RunManager(Service(settings, source_factory=lambda: source))


def new_run(service, limit=25):
    from reddit_analyzer.models import Run

    return service.create_run(Run(collection="demo", params=SearchParams(query="x", limit=limit)))


def wait_done(manager, timeout=5.0):
    end = time.monotonic() + timeout
    while manager.busy:
        assert time.monotonic() < end, "job did not finish in time"
        time.sleep(0.01)


def test_run_completes_and_logs_pages(settings):
    manager = make_manager(settings, FakeSource(total=25))
    manager.start(new_run(manager._service))
    wait_done(manager)
    job = manager.job
    assert job.error is None
    assert job.final.status is RunStatus.COMPLETED
    assert job.final.posts_fetched == 25
    assert sum(line.startswith("page ") for line in job.log) == 3
    with Database.open(settings) as db:
        assert db.count_posts("demo") == 25


def test_failure_is_reported_not_raised(settings):
    manager = make_manager(settings, FakeSource(total=25, fail_on_page_call=2))
    run = new_run(manager._service)
    manager.start(run)
    wait_done(manager)
    job = manager.job
    assert "simulated outage" in job.error
    assert job.final is None
    assert f"rpa runs resume {run.id}" in job.log[-1]


def test_cancel_stops_the_run(settings):
    release = threading.Event()

    class SlowSource(FakeSource):
        def iter_pages(self, *args, **kwargs):
            for page in super().iter_pages(*args, **kwargs):
                yield page
                release.wait(2)

    manager = make_manager(settings, SlowSource(total=50, page_size=10))
    manager.start(new_run(manager._service, limit=50))
    manager.cancel()
    release.set()
    wait_done(manager)
    assert manager.job.final.status is RunStatus.CANCELLED
    assert manager.job.final.posts_fetched < 50


def test_only_one_run_at_a_time(settings):
    release = threading.Event()

    class SlowSource(FakeSource):
        def iter_pages(self, *args, **kwargs):
            release.wait(2)
            yield from super().iter_pages(*args, **kwargs)

    manager = make_manager(settings, SlowSource(total=10))
    run = new_run(manager._service, limit=10)
    manager.start(run)
    with pytest.raises(RuntimeError, match="already running"):
        manager.start(run)
    release.set()
    wait_done(manager)


def test_resume_continues_an_interrupted_run(settings):
    source = FakeSource(total=25, fail_on_page_call=2)
    manager = make_manager(settings, source)
    run = new_run(manager._service)
    manager.start(run)
    wait_done(manager)
    assert manager.job.error
    saved = manager._service.get_run(run.id)
    assert saved.posts_fetched == 10

    manager.start(saved, resumed=True)
    wait_done(manager)
    assert manager.job.error is None
    assert manager.job.final.posts_fetched == 25
    assert manager.job.log[0].startswith("Resuming")

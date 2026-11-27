import sqlite3

import pytest
from fakes import FakeSource
from typer.testing import CliRunner

from reddit_analyzer.cli.main import app
from reddit_analyzer.collect.runner import run_collection
from reddit_analyzer.errors import ServerError
from reddit_analyzer.models import ListingParams, Run, SearchParams
from reddit_analyzer.sources.oauth import RedditClient
from reddit_analyzer.storage import Database

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_PATHS__DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def test_runs_list_empty():
    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0 and "No runs yet" in result.output


def test_runs_list_shows_runs_and_filters():
    with Database.open() as db:
        db.create_run(Run(collection="rust", params=SearchParams(query="rust lang")))
        db.create_run(Run(collection="italy", params=ListingParams(subreddit="italy", sort="top")))
    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0
    assert "rust lang" in result.output and "r/italy (top)" in result.output
    assert "pending" in result.output

    only = runner.invoke(app, ["runs", "list", "--collection", "rust"])
    assert "rust lang" in only.output and "italy" not in only.output


def test_resume_unknown_run_fails():
    result = runner.invoke(app, ["runs", "resume", "42"])
    assert result.exit_code == 1 and "does not exist" in result.output


def test_resume_continues_a_failed_run(monkeypatch):
    with Database.open() as db:
        run = db.create_run(Run(collection="rust", params=SearchParams(query="rust", limit=25)))
        with pytest.raises(ServerError):
            run_collection(db, FakeSource(total=25, fail_on_page_call=2), run)

    class FakeClient(FakeSource):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(RedditClient, "from_config", classmethod(lambda cls: FakeClient(total=25)))
    result = runner.invoke(app, ["runs", "resume", str(run.id)])

    assert result.exit_code == 0, result.output
    assert "Resuming run 1 from 10 posts" in result.output
    assert "page 1: 20 posts" in result.output and "Done: run 1 completed" in result.output
    with Database.open() as db:
        assert db.count_posts("rust") == 25

    again = runner.invoke(app, ["runs", "resume", str(run.id)])
    assert "already completed" in again.output


def test_import_legacy_command(tmp_path):
    legacy = tmp_path / "old.db"
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE posts (post_id, query_term, titolo, contenuto, categoria, punteggio,"
        " url_post, timestamp_retrieval)"
    )
    conn.execute(
        "INSERT INTO posts VALUES ('x1','ai','T','body','italy',1,"
        "'https://www.reddit.com/r/italy/comments/x1/t/','2025-01-01 00:00:00')"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["db", "import-legacy", str(legacy)])
    assert result.exit_code == 0, result.output
    assert "Imported 1 new posts into 1 new collections" in result.output

    missing = runner.invoke(app, ["db", "import-legacy", str(tmp_path / "nope.db")])
    assert missing.exit_code == 1

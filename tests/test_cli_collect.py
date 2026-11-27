import json
import re

import pytest
from fakes import FakeSource
from typer.testing import CliRunner

from reddit_analyzer.cli.main import app
from reddit_analyzer.errors import AuthError, RateLimitedError
from reddit_analyzer.models import ListingParams, SearchParams
from reddit_analyzer.sources.oauth import RedditClient
from reddit_analyzer.storage import Database

runner = CliRunner()


class FakeClient(FakeSource):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


@pytest.fixture(autouse=True)
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_PATHS__DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def fake_reddit(monkeypatch):
    holder = {"source": FakeClient(total=25)}
    monkeypatch.setattr(RedditClient, "from_config", classmethod(lambda cls: holder["source"]))
    return holder


def test_collect_search_stores_posts_and_params(fake_reddit):
    result = runner.invoke(
        app,
        ["collect", "search", "Rust lang", "-s", "r/programming", "-s", "rust", "--sort", "top",
         "-t", "month", "-n", "25", "--comments", "--depth", "3"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "Run 1 in collection 'rust-lang'" in result.output
    assert (
        "page 1: 10 posts" in result.output and "Done: run 1 completed, 25 posts" in result.output
    )
    with Database.open() as db:
        run = db.get_run(1)
        assert isinstance(run.params, SearchParams)
        assert run.params.subreddits == ["programming", "rust"]
        assert (run.params.sort, run.params.time, run.params.limit) == ("top", "month", 25)
        assert run.params.comments.depth == 3
        assert db.count_posts("rust-lang") == 25 and db.count_comments("rust-lang") == 50


def test_collect_subreddit_uses_name_as_collection(fake_reddit):
    result = runner.invoke(app, ["collect", "subreddit", "r/italy", "--sort", "top", "-n", "10"])
    assert result.exit_code == 0, result.output
    with Database.open() as db:
        run = db.get_run(1)
        assert run.collection == "italy" and isinstance(run.params, ListingParams)
        assert run.params.sort == "top"


def test_collect_json_prints_only_json(fake_reddit):
    result = runner.invoke(app, ["collect", "subreddit", "italy", "-n", "25", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["status"] == "completed" and data["posts_fetched"] == 25
    assert data["end_reason"] == "limit"


def test_quiet_hides_progress_but_keeps_the_result(fake_reddit):
    result = runner.invoke(app, ["-q", "collect", "subreddit", "italy", "-n", "25"])
    assert result.exit_code == 0
    assert "page 1" not in result.output and "Done: run 1 completed" in result.output


def test_quiet_and_verbose_conflict():
    result = runner.invoke(app, ["-q", "-v", "collections", "list"])
    assert result.exit_code == 2


def test_collect_failure_points_to_resume_and_sets_exit_code(fake_reddit):
    fake_reddit["source"] = FakeClient(total=25, fail_on_page_call=2)
    result = runner.invoke(app, ["collect", "subreddit", "italy", "-n", "25"])
    assert result.exit_code == 4  # simulated ServerError
    assert "rpa runs resume 1" in result.output
    with Database.open() as db:
        assert db.get_run(1).status.value == "failed"


@pytest.mark.parametrize(
    ("error", "code"), [(AuthError("bad key"), 3), (RateLimitedError("slow"), 4)]
)
def test_exit_codes_by_error_kind(monkeypatch, error, code):
    def boom(cls):
        raise error

    monkeypatch.setattr(RedditClient, "from_config", classmethod(boom))
    result = runner.invoke(app, ["collect", "subreddit", "italy"])
    assert result.exit_code == code


def test_invalid_option_is_a_usage_error():
    result = runner.invoke(app, ["collect", "search", "x", "--sort", "nonsense"])
    assert result.exit_code == 2


def test_collections_list_and_export(fake_reddit, tmp_path):
    empty = runner.invoke(app, ["collections", "list"])
    assert "No collections yet" in empty.output

    runner.invoke(app, ["collect", "subreddit", "italy", "-n", "25", "--comments"])
    listed = json.loads(runner.invoke(app, ["collections", "list", "--json"]).stdout)
    assert listed[0]["name"] == "italy" and listed[0]["posts"] == 25 and listed[0]["runs"] == 1
    assert "italy" in runner.invoke(app, ["collections", "list"]).output

    out = tmp_path / "exp"
    result = runner.invoke(app, ["export", "italy", "-f", "csv", "-o", str(out), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["stats"]["kept"] == 25
    assert (out / "italy.csv").exists() and (out / "dataset_card.md").exists()

    comments = runner.invoke(
        app, ["export", "italy", "--unit", "comment", "-o", str(tmp_path / "c")]
    )
    assert comments.exit_code == 0, comments.output
    assert "50 rows exported" in comments.output


def test_export_errors():
    missing = runner.invoke(app, ["export", "ghost"])
    assert missing.exit_code == 1 and "does not exist" in missing.output
    bad = runner.invoke(app, ["export", "Not Valid!"])
    assert bad.exit_code == 1 and "not a valid collection name" in bad.output


def test_runs_list_json(fake_reddit):
    runner.invoke(app, ["collect", "subreddit", "italy", "-n", "10"])
    data = json.loads(runner.invoke(app, ["runs", "list", "--json"]).stdout)
    assert data[0]["id"] == 1 and data[0]["collection"] == "italy"


def test_help_offers_shell_completion():
    result = runner.invoke(app, ["--help"])
    output = re.sub(r"\[[0-9;]*m", "", result.output)  # CI forces colors, which split flags
    assert "--install-completion" in output and "--quiet" in output

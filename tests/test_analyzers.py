"""Analyzers: registry and plugins, storage of results, and each built-in."""

from importlib.metadata import EntryPoint

import pytest
from fakes import make_post
from typer.testing import CliRunner

from reddit_analyzer import analyzers
from reddit_analyzer.analyzers import registry
from reddit_analyzer.cli.main import app
from reddit_analyzer.config import load_settings
from reddit_analyzer.errors import AnalyzerError
from reddit_analyzer.models import AnalysisResult, Run, SearchParams
from reddit_analyzer.storage import Database

EN = "I love this wonderful library, it is great and amazing to use every day"
IT = "Questo strumento funziona molto bene e mi piace davvero tanto, grazie a tutti"


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_DATA_DIR", str(tmp_path / "data"))
    return load_settings()


@pytest.fixture
def db(settings):
    """Collection 'demo': two English posts, one Italian, one too short to detect."""
    posts = [
        make_post(1, title="Rust is great", selftext=EN, subreddit="rust"),
        make_post(
            2,
            title="Terrible awful crash",
            selftext="This is the worst thing, I hate it and it is horrible and bad",
            subreddit="rust",
        ),
        make_post(3, title="Strumento", selftext=IT, subreddit="italy"),
        make_post(4, title="1234 !!!", selftext=""),
    ]
    with Database.open(settings) as database:
        run = database.create_run(Run(collection="demo", params=SearchParams(query="x")))
        database.upsert_posts(posts)
        database.link_posts(run.id, [p.id for p in posts])
        yield database


def test_results_are_stored_and_replaced(db):
    first = analyzers.run(db, "stats", "demo")
    assert first.data["posts"] == 4
    assert db.get_analysis("stats", "demo").data["posts"] == 4
    db.save_analysis(AnalysisResult(analyzer="stats", collection="demo", data={"posts": 99}))
    assert db.get_analysis("stats", "demo").data == {"posts": 99}
    assert db.get_analysis("stats", None) is None  # the whole database is a different key


def test_whole_database_results(db):
    analyzers.run(db, "stats")
    assert db.list_analyses(None)[0].collection is None


def test_stats_include_activity_heatmap(db):
    activity = analyzers.run(db, "stats", "demo").data["activity"]
    assert len(activity) == 7 and all(len(day) == 24 for day in activity)
    assert sum(map(sum, activity)) == 4


def test_unknown_analyzer_and_collection(db):
    with pytest.raises(AnalyzerError, match="Available: stats"):
        analyzers.run(db, "nope", "demo")
    with pytest.raises(AnalyzerError, match="does not exist"):
        analyzers.run(db, "stats", "ghost")


def test_keywords_rank_distinctive_words(db):
    data = analyzers.run(db, "keywords", "demo").data
    terms = [k["term"] for k in data["keywords"]]
    assert data["documents"] == 3  # the numeric-only post has no usable words
    assert "wonderful" in terms and "terrible" in terms
    assert "that" not in terms  # stopword


def test_language_is_detected_and_saved_on_posts(db):
    data = analyzers.run(db, "language", "demo").data
    assert data["languages"]["en"] == 2 and data["languages"]["it"] == 1
    assert data["languages"]["unknown"] == 1
    assert db.get_post("p0003").lang == "it"
    assert db.get_post("p0004").lang is None
    assert analyzers.run(db, "language", "demo").data["detected_now"] == 0  # nothing re-detected


def test_sentiment_scores_english_only(db):
    data = analyzers.run(db, "sentiment", "demo").data
    assert data["analyzed"] == 2
    assert data["skipped_not_english"] == 2  # the Italian post and the undetectable one
    assert data["labels"] == {"positive": 1, "neutral": 0, "negative": 1}
    assert data["by_month"][0][0] == "2026-01"


def test_missing_extra_gives_install_hint(db, monkeypatch):
    monkeypatch.setattr(registry, "find_spec", lambda name: None)
    with pytest.raises(AnalyzerError, match=r"reddit-post-analyzer\[nlp\]"):
        analyzers.run(db, "sentiment", "demo")


class Plugin(analyzers.Analyzer):
    name = "double"
    description = "Counts posts twice."

    def run(self, db, collection):
        return {"n": 2 * db.count_posts(collection)}

    def summary(self, data):
        return f"n={data['n']}"


def _entry_points(*eps):
    return lambda group: [ep for ep in eps if group == registry.GROUP]


def test_plugin_from_entry_point(db, monkeypatch):
    ep = EntryPoint("double", f"{__name__}:Plugin", registry.GROUP)
    monkeypatch.setattr(registry, "entry_points", _entry_points(ep))
    assert "double" in analyzers.available()
    assert analyzers.run(db, "double", "demo").data == {"n": 8}


def test_broken_or_clashing_plugins_are_skipped(monkeypatch, caplog):
    broken = EntryPoint("broken", "no_such_module:Nothing", registry.GROUP)
    clash = EntryPoint("stats", "reddit_analyzer.analyzers.stats:StatsAnalyzer", registry.GROUP)
    notanalyzer = EntryPoint("odd", "builtins:object", registry.GROUP)
    monkeypatch.setattr(registry, "entry_points", _entry_points(broken, clash, notanalyzer))
    found = analyzers.available()
    assert set(found) == {c.name for c in registry.BUILTIN}
    assert caplog.text.count("Skipping analyzer plugin") == 3


# -- CLI ------------------------------------------------------------------------------------

runner = CliRunner()


def test_cli_runs_ready_analyzers_and_shows_them(db):
    result = runner.invoke(app, ["analyze", "demo", "-a", "keywords", "--json"])
    assert result.exit_code == 0, result.output
    assert '"keywords"' in result.output
    shown = runner.invoke(app, ["analyze", "demo", "--show"])
    assert "== keywords" in shown.output and "== sentiment" not in shown.output


def test_cli_list_and_errors(db):
    listing = runner.invoke(app, ["analyze", "--list"])
    assert listing.exit_code == 0 and "sentiment" in listing.output
    bad = runner.invoke(app, ["analyze", "demo", "-a", "nope"])
    assert bad.exit_code == 1 and "Unknown analyzer" in bad.output


def test_cli_skips_missing_extras_unless_asked(db, monkeypatch):
    monkeypatch.setattr(registry, "find_spec", lambda name: None)
    default = runner.invoke(app, ["analyze", "demo", "--json"])
    assert default.exit_code == 0
    assert '"language"' in default.output  # listed under "skipped"
    explicit = runner.invoke(app, ["analyze", "demo", "-a", "language"])
    assert explicit.exit_code == 1

"""Web UI pages, driven with Streamlit's AppTest and an in-memory source."""

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from fakes import FakeSource, make_comment, make_post  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from reddit_analyzer.config import load_settings  # noqa: E402
from reddit_analyzer.gui import streamlit_app  # noqa: E402
from reddit_analyzer.gui.jobs import RunManager  # noqa: E402
from reddit_analyzer.gui.state import OVERRIDE_KEY, Context  # noqa: E402
from reddit_analyzer.models import Run, SearchParams  # noqa: E402
from reddit_analyzer.service import Service  # noqa: E402
from reddit_analyzer.storage import Database  # noqa: E402


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    return load_settings()


@pytest.fixture
def seeded(settings):
    posts = [
        make_post(i, subreddit="python" if i % 2 else "rust", title=f"Learning topic {i}")
        for i in range(1, 7)
    ]
    with Database.open(settings) as db:
        run = db.create_run(Run(collection="demo", params=SearchParams(query="learn")))
        db.upsert_posts(posts)
        db.link_posts(run.id, [p.id for p in posts])
        db.upsert_comments([make_comment(1, 0), make_comment(1, 1)])
    return settings


def _render(module: str) -> None:
    import importlib

    importlib.import_module(f"reddit_analyzer.gui.pages.{module}").render()


def open_app(settings, page: str, source=None) -> AppTest:
    """Run one page's ``render`` on its own (AppTest cannot pick a ``st.navigation`` page)."""
    service = Service(settings, source_factory=(lambda: source) if source else None)
    at = AppTest.from_function(_render, args=(page,), default_timeout=30)
    at.session_state[OVERRIDE_KEY] = Context(service, RunManager(service))
    return at.run()


def test_entry_script_builds_the_navigation(seeded):
    at = AppTest.from_file(streamlit_app.__file__, default_timeout=30).run()
    assert not at.exception


def test_collect_page_lists_collections(seeded):
    at = open_app(seeded, "collect")
    assert not at.exception
    assert at.title[0].value == "Collect"
    assert at.dataframe[0].value["Name"].tolist() == ["demo"]


def test_collect_form_rejects_empty_input(settings):
    at = open_app(settings, "collect")
    at.button[0].click().run()  # the form's Start button
    assert at.error[0].value == "Type the keywords or the subreddit first."


def test_collect_form_starts_a_run(settings):
    at = open_app(settings, "collect", source=FakeSource(total=5))
    at.text_input[0].input("learning")  # inside a form: applied by the submit below
    at.button[0].click().run()
    assert not at.exception
    with Database.open(settings) as db:
        assert [c.name for c in db.list_collections()] == ["learning"]


def test_explore_searches_posts(seeded):
    at = open_app(seeded, "explore")
    assert not at.exception
    assert len(at.dataframe[0].value) == 6
    at.text_input[0].input("topic 3").run()
    assert at.dataframe[0].value["Title"].tolist() == ["Learning topic 3"]


def test_explore_empty_database(settings):
    at = open_app(settings, "explore")
    assert at.info[0].value.startswith("Nothing collected yet")


def test_analysis_shows_metrics(seeded):
    at = open_app(seeded, "analysis")
    assert not at.exception
    assert [m.label for m in at.metric] == ["Posts", "Comments", "Mean score", "Period"]
    assert at.metric[0].value == "6"


def test_dataset_previews_the_template(seeded):
    at = open_app(seeded, "dataset")
    assert not at.exception
    assert [m.label for m in at.metric] == ["Rows kept", "Candidates"]


def test_dataset_shows_recipe_errors(seeded):
    at = open_app(seeded, "dataset")
    at.text_area[0].input("name: [unclosed").run()
    assert at.error and "YAML" in at.error[0].value


def test_settings_page_shows_paths(settings):
    at = open_app(settings, "settings")
    assert not at.exception
    assert any("reddit.db" in m.value for m in at.markdown)

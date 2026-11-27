"""Terminal UI tests: drive the real screens with Textual's pilot and an in-memory source."""

import pytest

pytest.importorskip("textual")

from fakes import FakeSource, make_comment, make_post  # noqa: E402
from textual.widgets import Button, DataTable, Input, Select, Sparkline, Static  # noqa: E402

from reddit_analyzer.config import load_settings  # noqa: E402
from reddit_analyzer.errors import AuthError  # noqa: E402
from reddit_analyzer.models import Run, SearchParams  # noqa: E402
from reddit_analyzer.stats import collection_stats  # noqa: E402
from reddit_analyzer.storage import Database  # noqa: E402
from reddit_analyzer.tui.app import RpaApp  # noqa: E402
from reddit_analyzer.tui.service import Service  # noqa: E402

SIZE = (150, 50)


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    return load_settings()


@pytest.fixture
def seeded(settings):
    """A database with collection 'demo': 6 posts in 2 subreddits, comments on the first."""
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


def make_app(settings, source=None):
    factory = (lambda: source) if source is not None else None
    return RpaApp(Service(settings, source_factory=factory))


async def wait_until(pilot, condition, tries=100):
    for _ in range(tries):
        if condition():
            return
        await pilot.pause(0.05)
    raise AssertionError("condition not reached in time")


def rows(table: DataTable) -> list[list[str]]:
    return [[str(c) for c in table.get_row_at(i)] for i in range(table.row_count)]


def test_stats_counts_and_rankings(seeded):
    with Database.open(seeded) as db:
        stats = collection_stats(db, "demo")
    assert stats.posts == 6
    assert stats.comments == 2
    assert dict(stats.top_subreddits) == {"python": 3, "rust": 3}
    assert stats.posts_per_month == [("2026-01", 6)]
    assert "learning" in dict(stats.top_words)


def test_stats_of_empty_database(settings):
    with Database.open(settings) as db:
        assert collection_stats(db).posts == 0


async def test_dashboard_lists_collections_and_runs(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert rows(screen.query_one("#collections", DataTable)) == [["demo", "6", "2", "1"]]
        assert rows(screen.query_one("#runs", DataTable))[0][1:3] == ["pending", "demo"]


async def test_collection_selected_in_dashboard_opens_browser(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.pause()
        pilot.app.screen.query_one("#collections", DataTable).focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert pilot.app.collection == "demo"
        assert pilot.app.screen.query_one("#posts", DataTable).row_count == 6


async def test_browser_search_filter_and_preview(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f3")
        await pilot.pause()
        screen = pilot.app.screen
        posts = screen.query_one("#posts", DataTable)
        assert posts.row_count == 6

        screen.query_one("#b-sub", Input).value = "r/Rust"
        screen.query_one("#b-sub", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert posts.row_count == 3

        screen.query_one("#b-search", Input).value = "topic 4"
        screen.query_one("#b-search", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert [r[3] for r in rows(posts)] == ["Learning topic 4"]


async def test_browser_preview_shows_comments(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f3")
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#b-search", Input).value = "topic 1"
        screen.query_one("#b-search", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        preview = str(screen.query_one("#preview", Static).render())
        assert "Learning topic 1" in preview
        assert "Comments stored locally: 2" in preview


async def test_collect_runs_a_search_from_the_form(settings):
    source = FakeSource(total=25, page_size=10, comments_per_post=0)
    async with make_app(settings, source).run_test(size=SIZE) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#query", Input).value = "Machine Learning"
        screen.query_one("#limit", Input).value = "25"
        await pilot.click("#start")
        status = screen.query_one("#status", Static)
        await wait_until(pilot, lambda: "completed: 25 posts" in str(status.render()))
        assert "collection 'machine-learning'" in str(status.render())
        assert not screen.query_one("#start", Button).disabled
    with Database.open(settings) as db:
        assert db.count_posts("machine-learning") == 25


async def test_collect_needs_input(settings):
    async with make_app(settings, FakeSource()).run_test(size=SIZE) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        await pilot.click("#start")
        await pilot.pause()
        with Database.open(settings) as db:
            assert db.list_runs() == []


async def test_collect_reports_missing_credentials_and_stays_usable(settings):
    def no_credentials():
        raise AuthError("No Reddit credentials. See docs/reddit-credentials.md")

    app = RpaApp(Service(settings, source_factory=no_credentials))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#query", Input).value = "rust"
        await pilot.click("#start")
        status = screen.query_one("#status", Static)
        await wait_until(pilot, lambda: "failed" in str(status.render()))
        assert not screen.query_one("#start", Button).disabled
        with Database.open(settings) as db:  # the run exists, so it can be resumed later
            assert db.list_runs()[0].collection == "rust"


async def test_dashboard_resumes_an_unfinished_run(settings):
    with Database.open(settings) as db:
        db.create_run(Run(collection="rust", params=SearchParams(query="rust", limit=15)))
    source = FakeSource(total=15, page_size=10, comments_per_post=0)
    async with make_app(settings, source).run_test(size=SIZE) as pilot:
        await pilot.pause()
        dashboard = pilot.app.screen
        dashboard.query_one("#runs", DataTable).focus()
        await pilot.press("u")
        await pilot.pause()
        collect = pilot.app.screen
        status = collect.query_one("#status", Static)
        await wait_until(pilot, lambda: "completed: 15 posts" in str(status.render()))
    with Database.open(settings) as db:
        assert db.count_posts("rust") == 15
        assert db.list_runs()[0].status.value == "completed"


async def test_dataset_preview_updates_while_typing(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f4")
        screen = pilot.app.screen
        status = screen.query_one("#recipe-status", Static)
        table = screen.query_one("#preview-rows", DataTable)
        await wait_until(pilot, lambda: "rows kept out of 6" in str(status.render()), tries=200)

        screen.query_one("#recipe-editor").load_text(
            "name: x\ncollection: demo\nfilters: {min_score: 5}\n"
        )
        await wait_until(pilot, lambda: "2 rows kept out of 6" in str(status.render()))
        assert table.row_count == 2


async def test_dataset_shows_recipe_errors(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f4")
        screen = pilot.app.screen
        screen.query_one("#recipe-editor").load_text("name: Bad Name\ncollection: demo\n")
        status = screen.query_one("#recipe-status", Static)
        await wait_until(pilot, lambda: "Invalid recipe" in str(status.render()), tries=200)


async def test_dataset_build_writes_files(seeded, tmp_path):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f4")
        screen = pilot.app.screen
        await pilot.pause(0.1)
        await pilot.click("#d-build")
        await wait_until(
            pilot, lambda: (tmp_path / "out" / "my-dataset" / "dataset_card.md").exists()
        )
        assert (tmp_path / "out" / "my-dataset" / "my-dataset.jsonl").exists()
        await wait_until(pilot, lambda: not screen.query_one("#d-build", Button).disabled)


async def test_dataset_save_and_pick_recipe(seeded, tmp_path):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f4")
        screen = pilot.app.screen
        await pilot.pause(0.1)
        screen.query_one("#d-path", Input).value = "recipes/saved.yaml"
        await pilot.click("#d-save")
        await pilot.pause()
        assert "collection: demo" in (tmp_path / "recipes" / "saved.yaml").read_text()
        await pilot.press("f1")
        await pilot.press("f4")
        await pilot.pause()
        select = screen.query_one("#d-file", Select)
        assert select.value == ""
        assert len(list(select._options)) == 2  # template + the saved recipe


async def test_analysis_screen_shows_statistics(seeded):
    async with make_app(seeded).run_test(size=SIZE) as pilot:
        await pilot.press("f5")
        screen = pilot.app.screen
        summary = screen.query_one("#analysis-summary", Static)
        await wait_until(pilot, lambda: "6 posts" in str(summary.render()))
        assert rows(screen.query_one("#t-subs", DataTable)) == [["python", "3"], ["rust", "3"]]
        assert list(screen.query_one("#months", Sparkline).data) == [6.0]


async def test_keys_switch_screens(settings):
    async with make_app(settings).run_test(size=SIZE) as pilot:
        for key, name in [
            ("f2", "CollectScreen"),
            ("f3", "BrowserScreen"),
            ("f4", "DatasetScreen"),
            ("f5", "AnalysisScreen"),
            ("f1", "DashboardScreen"),
        ]:
            await pilot.press(key)
            await pilot.pause()
            assert type(pilot.app.screen).__name__ == name


async def test_collect_form_fits_a_small_terminal(settings):
    async with make_app(settings).run_test(size=(100, 30)) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        screen = pilot.app.screen
        for widget_id in ("#query", "#comments", "#name", "#start", "#progress"):
            region = screen.query_one(widget_id).region
            assert region.bottom <= 30, f"{widget_id} is cut off at {region}"
        assert screen.query_one("#collect-log").region.height >= 4


class GatedSource(FakeSource):
    """Serves the first page, then waits until the test lets it continue."""

    def __init__(self, gate, **kwargs):
        super().__init__(**kwargs)
        self.gate = gate

    def iter_pages(self, params, after=None, fetched=0):
        for n, page in enumerate(super().iter_pages(params, after, fetched)):
            if n:
                self.gate.wait(timeout=5)
            yield page


async def test_collect_can_be_cancelled_and_resumed(settings):
    import threading

    gate = threading.Event()
    source = GatedSource(gate, total=40, page_size=10, comments_per_post=0)
    async with make_app(settings, source).run_test(size=SIZE) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#query", Input).value = "rust"
        screen.query_one("#limit", Input).value = "40"
        await pilot.click("#start")
        with Database.open(settings) as db:
            await wait_until(pilot, lambda: db.count_posts() >= 10)
        await pilot.click("#cancel")
        gate.set()
        status = screen.query_one("#status", Static)
        await wait_until(pilot, lambda: "cancelled" in str(status.render()))
        assert not screen.query_one("#start", Button).disabled
    with Database.open(settings) as db:
        run = db.list_runs()[0]
        assert run.status.value == "cancelled"
        assert 10 <= run.posts_fetched < 40


def test_dashboard_snapshot(snap_compare, seeded):
    assert snap_compare(make_app(seeded), terminal_size=(100, 30))


def test_collect_snapshot(snap_compare, settings):
    assert snap_compare(make_app(settings), terminal_size=(100, 30), press=["f2"])

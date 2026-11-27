import pytest
from fakes import make_post
from typer.testing import CliRunner

from reddit_analyzer.cli.main import app
from reddit_analyzer.models import Run, SearchParams
from reddit_analyzer.storage import Database

runner = CliRunner()

RECIPE = """\
name: demo
collection: rust
filters: {min_score: 5}
output: {format: jsonl, fields: [id, score, text]}
"""


@pytest.fixture(autouse=True)
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("RPA_PATHS__DATA_DIR", str(tmp_path / "data"))
    with Database.open() as db:
        run = db.create_run(Run(collection="rust", params=SearchParams(query="rust")))
        posts = [make_post(i, score=i, title=f"Title {i}") for i in range(1, 11)]
        db.upsert_posts(posts)
        db.link_posts(run.id, [p.id for p in posts])


@pytest.fixture
def recipe_file(tmp_path):
    path = tmp_path / "demo.yaml"
    path.write_text(RECIPE, encoding="utf-8")
    return path


def test_preview_shows_stats_and_rows_without_writing(recipe_file, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["dataset", "preview", str(recipe_file), "-n", "2"])
    assert result.exit_code == 0, result.output
    assert "6 rows kept out of 10 post candidates" in result.output
    assert "dropped      4  score" in result.output
    assert result.output.count("- [python") == 2
    assert not (tmp_path / "out").exists()


def test_build_writes_files(recipe_file, tmp_path):
    out = tmp_path / "ds"
    result = runner.invoke(app, ["dataset", "build", str(recipe_file), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert len((out / "demo.jsonl").read_text(encoding="utf-8").splitlines()) == 6
    assert "Dataset card: demo" in (out / "dataset_card.md").read_text(encoding="utf-8")


def test_errors_are_friendly(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: x\ncollection: rust\nfilters: {min_scor: 1}\n", encoding="utf-8")
    result = runner.invoke(app, ["dataset", "build", str(bad)])
    assert result.exit_code == 1 and "filters.min_scor: unknown option" in result.output

    missing = runner.invoke(app, ["dataset", "preview", str(tmp_path / "nope.yaml")])
    assert missing.exit_code == 1 and "Cannot read recipe" in missing.output

    other = tmp_path / "other.yaml"
    other.write_text("name: x\ncollection: ghost\n", encoding="utf-8")
    ghost = runner.invoke(app, ["dataset", "build", str(other)])
    assert ghost.exit_code == 1 and "Existing collections: rust" in ghost.output

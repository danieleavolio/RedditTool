from pathlib import Path

import pytest

from reddit_analyzer.datasets.recipe import load_recipe, parse_recipe, recipe_to_yaml
from reddit_analyzer.errors import DatasetError

ROOT = Path(__file__).parent.parent


def _recipe(**extra):
    return parse_recipe({"name": "demo", "collection": "c", **extra})


def test_minimal_recipe_gets_defaults():
    r = _recipe()
    assert r.unit == "post" and r.output.format == "jsonl"
    assert r.filters.exclude_removed is True and r.filters.nsfw == "include"
    assert r.fields == ["id", "subreddit", "created_utc", "score", "num_comments", "text"]
    assert _recipe(unit="pair").fields[-1] == "response"


def test_example_recipe_is_valid():
    r = load_recipe(ROOT / "recipes" / "examples" / "ai-italia.yaml")
    assert r.split and list(r.split.parts) == ["a", "b"]
    assert r.filters.lang == ["it"] and r.filters.subreddits == ["italy", "italiapersonalfinance"]


def test_yaml_date_becomes_utc_midnight(tmp_path):
    path = tmp_path / "r.yaml"
    path.write_text("name: d\ncollection: c\nfilters: {after: 2026-03-01}\n", encoding="utf-8")
    after = load_recipe(path).filters.after
    assert (after.year, after.month, after.day, after.hour) == (2026, 3, 1, 0)
    assert after.utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    ("extra", "needle"),
    [
        ({"filters": {"min_scor": 1}}, "filters.min_scor: unknown option"),
        ({"unit": "thread"}, "unit"),
        ({"transform": {"text": "{titel}"}}, "unknown placeholder {titel}"),
        ({"transform": {"text": "{text}"}}, "unknown placeholder {text}"),
        ({"unit": "comment", "output": {"fields": ["selftext"]}}, "unknown field 'selftext'"),
        ({"split": {"parts": {"a": 0.5, "b": 0.4}}}, "must sum to 1"),
        ({"split": {"parts": {"a": 1.0}}}, "at least two parts"),
        ({"filters": {"after": "2026-02-01", "before": "2026-01-01"}}, "earlier than 'before'"),
        ({"filters": {"min_chars": 50, "max_chars": 10}}, "min_chars"),
        ({"transform": {"strip": ["emoji"]}}, "transform.strip"),
    ],
)
def test_invalid_recipes_say_where_and_why(extra, needle):
    with pytest.raises(DatasetError, match="Invalid recipe") as err:
        _recipe(**extra)
    assert needle in str(err.value)


def test_not_a_mapping_and_bad_files(tmp_path):
    with pytest.raises(DatasetError, match="mapping"):
        parse_recipe(["a"])
    with pytest.raises(DatasetError, match="Cannot read"):
        load_recipe(tmp_path / "missing.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: [unclosed", encoding="utf-8")
    with pytest.raises(DatasetError, match="not valid YAML"):
        load_recipe(bad)


def test_recipe_round_trips_through_yaml():
    r = _recipe(filters={"lang": "it", "min_score": 3}, split={"parts": {"a": 0.7, "b": 0.3}})
    assert parse_recipe(__import__("yaml").safe_load(recipe_to_yaml(r))) == r

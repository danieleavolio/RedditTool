import csv
import json

import pytest

from reddit_analyzer.errors import DatasetError
from reddit_analyzer.export import get_writer

FIELDS = {"id": "str", "score": "int", "ratio": "float", "nsfw": "bool", "text": "str"}
ROWS = [
    {"id": "a", "score": 3, "ratio": 0.5, "nsfw": False, "text": 'ciao, "mondo"\nè così'},
    {"id": "b", "score": -1, "ratio": None, "nsfw": True, "text": None, "extra": "ignored"},
]


def _write(fmt, path):
    w = get_writer(fmt)(path, FIELDS)
    for row in ROWS:
        w.write(row)
    w.close()


def test_csv_round_trip(tmp_path):
    path = tmp_path / "x.csv"
    _write("csv", path)
    assert b"\r" not in path.read_bytes()
    with open(path, encoding="utf-8", newline="") as f:
        table = list(csv.reader(f))
    assert table[0] == list(FIELDS)
    assert table[1] == ["a", "3", "0.5", "false", 'ciao, "mondo"\nè così']
    assert table[2] == ["b", "-1", "", "true", ""]


def test_jsonl_round_trip(tmp_path):
    path = tmp_path / "x.jsonl"
    _write("jsonl", path)
    raw = path.read_bytes()
    assert b"\r" not in raw and "è così".encode() in raw  # real UTF-8, not \u escapes
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    assert rows[0] == {k: ROWS[0][k] for k in FIELDS}
    assert rows[1]["ratio"] is None and "extra" not in rows[1]


def test_parquet_round_trip_and_empty_file(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")
    path = tmp_path / "x.parquet"
    _write("parquet", path)
    table = pq.read_table(path)
    assert table.column_names == list(FIELDS)
    assert table.to_pylist() == [{k: r[k] for k in FIELDS} for r in ROWS]
    assert str(table.schema.field("score").type) == "int64"

    empty = tmp_path / "empty.parquet"
    get_writer("parquet")(empty, FIELDS).close()
    assert pq.read_table(empty).num_rows == 0


def test_hf_saves_a_loadable_folder(tmp_path):
    datasets = pytest.importorskip("datasets")
    path = tmp_path / "ds"
    _write("hf", path)
    loaded = datasets.load_from_disk(str(path))
    assert loaded.column_names == list(FIELDS) and loaded[1]["ratio"] is None


def test_abort_removes_the_output(tmp_path):
    path = tmp_path / "x.jsonl"
    w = get_writer("jsonl")(path, FIELDS)
    w.write(ROWS[0])
    w.abort()
    assert not path.exists()


def test_unknown_format_and_missing_extra(monkeypatch):
    with pytest.raises(DatasetError, match="Unknown format 'xml'"):
        get_writer("xml")
    import builtins

    real_import = builtins.__import__

    def no_pyarrow(name, *a, **k):
        if name.startswith("pyarrow"):
            raise ImportError(name)
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_pyarrow)
    monkeypatch.delitem(__import__("sys").modules, "reddit_analyzer.export.parquet", raising=False)
    with pytest.raises(DatasetError, match=r"reddit-post-analyzer\[parquet\]"):
        get_writer("parquet")

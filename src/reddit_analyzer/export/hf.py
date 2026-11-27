"""Hugging Face ``datasets`` output, saved to a local folder (``Dataset.save_to_disk``).

Needs the ``[hf]`` extra. Nothing is ever uploaded. Load it back with
``datasets.load_from_disk(path)``. With a split, every part is its own folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from datasets import Dataset, Features, Value

from reddit_analyzer.export.base import RowWriter

_TYPES = {"str": "string", "int": "int64", "float": "float64", "bool": "bool"}


class HfWriter(RowWriter):
    suffix = ""

    def __init__(self, path: Path, fields: dict[str, str]):
        super().__init__(path, fields)
        self._features = Features({n: Value(_TYPES[k]) for n, k in fields.items()})
        self._rows: list[dict[str, Any]] = []  # the library wants the whole table at once

    def write(self, row: dict[str, Any]) -> None:
        self._rows.append({f: row[f] for f in self.fields})

    def close(self) -> None:
        Dataset.from_list(self._rows, features=self._features).save_to_disk(str(self.path))

    def abort(self) -> None:
        self._remove()

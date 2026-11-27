from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reddit_analyzer.export.base import RowWriter


class JsonlWriter(RowWriter):
    """One JSON object per line, columns in recipe order, UTF-8, ``\\n`` line ends."""

    suffix = ".jsonl"

    def __init__(self, path: Path, fields: dict[str, str]):
        super().__init__(path, fields)
        self._file = open(path, "w", encoding="utf-8", newline="\n")  # noqa: SIM115

    def write(self, row: dict[str, Any]) -> None:
        self._file.write(json.dumps({f: row[f] for f in self.fields}, ensure_ascii=False) + "\n")

    def close(self) -> None:
        self._file.close()

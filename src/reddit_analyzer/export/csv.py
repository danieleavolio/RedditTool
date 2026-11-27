from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from reddit_analyzer.export.base import RowWriter


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


class CsvWriter(RowWriter):
    """UTF-8, comma separated, ``\\n`` line ends on every platform, header row first."""

    suffix = ".csv"

    def __init__(self, path: Path, fields: dict[str, str]):
        super().__init__(path, fields)
        self._file = open(path, "w", encoding="utf-8", newline="")  # noqa: SIM115
        self._csv = csv.writer(self._file, lineterminator="\n")
        self._csv.writerow(fields)

    def write(self, row: dict[str, Any]) -> None:
        self._csv.writerow([_cell(row[f]) for f in self.fields])

    def close(self) -> None:
        self._file.close()

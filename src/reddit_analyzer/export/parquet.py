"""Parquet output. Needs the ``[parquet]`` extra (pyarrow)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from reddit_analyzer.export.base import RowWriter

_TYPES = {"str": pa.string(), "int": pa.int64(), "float": pa.float64(), "bool": pa.bool_()}
_BATCH = 5000


class ParquetWriter(RowWriter):
    suffix = ".parquet"

    def __init__(self, path: Path, fields: dict[str, str]):
        super().__init__(path, fields)
        self._schema = pa.schema([(name, _TYPES[kind]) for name, kind in fields.items()])
        self._writer = pq.ParquetWriter(path, self._schema, compression="zstd")
        self._buffer: list[dict[str, Any]] = []

    def write(self, row: dict[str, Any]) -> None:
        self._buffer.append({f: row[f] for f in self.fields})
        if len(self._buffer) >= _BATCH:
            self._flush()

    def _flush(self) -> None:
        if self._buffer:
            self._writer.write_table(pa.Table.from_pylist(self._buffer, schema=self._schema))
            self._buffer = []

    def close(self) -> None:
        self._flush()
        self._writer.close()

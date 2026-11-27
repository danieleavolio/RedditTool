"""Exporters. Heavy ones (Parquet, Hugging Face) are imported only when asked for."""

from __future__ import annotations

from importlib import import_module

from reddit_analyzer.errors import DatasetError
from reddit_analyzer.export.base import RowWriter

# format -> (module, class, extra that provides its dependency or None)
_FORMATS = {
    "csv": ("csv", "CsvWriter", None),
    "jsonl": ("jsonl", "JsonlWriter", None),
    "parquet": ("parquet", "ParquetWriter", "parquet"),
    "hf": ("hf", "HfWriter", "hf"),
}


def get_writer(fmt: str) -> type[RowWriter]:
    try:
        module, cls, extra = _FORMATS[fmt]
    except KeyError:
        raise DatasetError(
            f"Unknown format {fmt!r}. Choose one of: {', '.join(_FORMATS)}."
        ) from None
    try:
        return getattr(import_module(f"reddit_analyzer.export.{module}"), cls)
    except ImportError as exc:
        raise DatasetError(
            f"The {fmt} format needs an extra package. "
            f"Install it with: pip install reddit-post-analyzer[{extra}]"
        ) from exc


__all__ = ["RowWriter", "get_writer"]

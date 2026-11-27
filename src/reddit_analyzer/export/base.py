"""Row writers. One writer per output file; the builder feeds it rows and closes it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class RowWriter(ABC):
    suffix: str  # file extension, or "" when the output is a directory

    def __init__(self, path: Path, fields: dict[str, str]):
        """``fields`` maps each output column, in order, to its type (str/int/float/bool)."""
        self.path = path
        self.fields = fields

    @abstractmethod
    def write(self, row: dict[str, Any]) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    def abort(self) -> None:
        """Called instead of ``close`` when the build failed. Leaves no half-written output."""
        try:
            self.close()
        finally:
            self._remove()

    def _remove(self) -> None:
        import shutil

        if self.path.is_dir():
            shutil.rmtree(self.path, ignore_errors=True)
        else:
            self.path.unlink(missing_ok=True)

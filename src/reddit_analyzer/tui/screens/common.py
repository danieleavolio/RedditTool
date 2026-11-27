"""Helpers shared by the screens that pick a collection."""

from __future__ import annotations

from textual.screen import Screen
from textual.widgets import Select

ALL = ""  # the Select value for "every collection"


class CollectionPicker(Screen):
    """A screen with a collection ``Select``. Refilling it programmatically must not be
    mistaken for the user choosing a collection, because ``Select.Changed`` can arrive late."""

    _syncing = False

    def fill_select(self, select: Select, options: list[tuple[str, str]], wanted: str) -> None:
        self._syncing = True
        select.set_options(options)
        select.value = wanted if wanted in {value for _, value in options} else ALL
        self.call_after_refresh(self._done_syncing)

    def _done_syncing(self) -> None:
        self.call_after_refresh(setattr, self, "_syncing", False)

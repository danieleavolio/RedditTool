"""The analyzer interface. Subclass ``Analyzer`` and expose it as an entry point to add one."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from reddit_analyzer.storage import Database


class Analyzer:
    """Computes something about a collection and returns it as JSON-serializable data.

    Plugins register in ``pyproject.toml``::

        [project.entry-points."reddit_analyzer.analyzers"]
        mine = "my_package:MyAnalyzer"
    """

    name: ClassVar[str]
    description: ClassVar[str] = ""
    requires: ClassVar[tuple[str, ...]] = ()  # importable modules the analyzer needs
    extra: ClassVar[str] = ""  # the pip extra that installs ``requires``, shown in errors

    def run(self, db: Database, collection: str | None) -> dict[str, Any]:
        """Analyze ``collection`` (``None``: everything). Must not print or prompt."""
        raise NotImplementedError

    def summary(self, data: dict[str, Any]) -> str:
        """A few readable lines for the CLI and the TUI."""
        return ""

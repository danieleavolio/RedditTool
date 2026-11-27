"""Finding and running analyzers: the built-ins plus plugins from entry points."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from importlib.util import find_spec

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.analyzers.keywords import KeywordsAnalyzer
from reddit_analyzer.analyzers.language import LanguageAnalyzer
from reddit_analyzer.analyzers.sentiment import SentimentAnalyzer
from reddit_analyzer.analyzers.stats import StatsAnalyzer
from reddit_analyzer.errors import AnalyzerError
from reddit_analyzer.models import AnalysisResult
from reddit_analyzer.storage import Database

GROUP = "reddit_analyzer.analyzers"
BUILTIN: tuple[type[Analyzer], ...] = (
    StatsAnalyzer,
    KeywordsAnalyzer,
    LanguageAnalyzer,
    SentimentAnalyzer,
)
log = logging.getLogger(__name__)


def available() -> dict[str, Analyzer]:
    """Every installed analyzer by name. A broken or clashing plugin is skipped with a warning."""
    found: dict[str, Analyzer] = {cls.name: cls() for cls in BUILTIN}
    for ep in entry_points(group=GROUP):
        try:
            loaded = ep.load()
            analyzer = loaded() if isinstance(loaded, type) else loaded
            if not isinstance(analyzer, Analyzer):
                raise TypeError("not an Analyzer")
            if analyzer.name in found:
                raise ValueError(f"the name {analyzer.name!r} is already taken")
        except Exception as exc:  # a plugin must never break the tool
            log.warning("Skipping analyzer plugin %r: %s", ep.name, exc)
            continue
        found[analyzer.name] = analyzer
    return found


def get(name: str) -> Analyzer:
    analyzers = available()
    if name not in analyzers:
        raise AnalyzerError(f"Unknown analyzer {name!r}. Available: {', '.join(analyzers)}.")
    return analyzers[name]


def missing_requirements(analyzer: Analyzer) -> list[str]:
    return [m for m in analyzer.requires if find_spec(m) is None]


def install_hint(analyzer: Analyzer) -> str:
    missing = ", ".join(missing_requirements(analyzer))
    how = (
        f'pip install "reddit-post-analyzer[{analyzer.extra}]"'
        if analyzer.extra
        else f"pip install {missing}"
    )
    return f"Analyzer {analyzer.name!r} needs {missing}. Install it with: {how}"


def run(db: Database, name: str, collection: str | None = None) -> AnalysisResult:
    """Run one analyzer and store its result, replacing the previous one."""
    analyzer = get(name)
    if missing_requirements(analyzer):
        raise AnalyzerError(install_hint(analyzer))
    if collection is not None and db.get_collection(collection) is None:
        raise AnalyzerError(f"Collection {collection!r} does not exist.")
    result = AnalysisResult(analyzer=name, collection=collection, data=analyzer.run(db, collection))
    db.save_analysis(result)
    return result

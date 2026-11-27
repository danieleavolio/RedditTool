"""Analyzers: pluggable computations over a collection, stored so the UIs just display them."""

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.analyzers.registry import (
    available,
    get,
    install_hint,
    missing_requirements,
    run,
)

__all__ = ["Analyzer", "available", "get", "install_hint", "missing_requirements", "run"]

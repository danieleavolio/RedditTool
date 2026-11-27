"""Kept for compatibility: the service now lives in ``reddit_analyzer.service``."""

from reddit_analyzer.service import CollectionRow, Service, recipe_from_text

__all__ = ["CollectionRow", "Service", "recipe_from_text"]

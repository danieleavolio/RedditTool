"""Detects the language of each post and stores it in ``posts.lang``."""

from __future__ import annotations

from collections import Counter
from typing import Any

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.datasets.filters import detect_language
from reddit_analyzer.storage import Database
from reddit_analyzer.text import post_text


class LanguageAnalyzer(Analyzer):
    name = "language"
    description = "Language of every post (saved on the post, also used by dataset filters)."
    requires = ("langdetect",)
    extra = "nlp"

    def run(self, db: Database, collection: str | None) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        found: dict[str, str] = {}
        for post in db.iter_posts(collection=collection):
            lang = post.lang
            if lang is None:  # already known languages are kept, never re-detected
                lang = detect_language(post_text(post))
                if lang:
                    found[post.id] = lang
            counts[lang or "unknown"] += 1
        db.set_post_languages(found)
        return {"languages": dict(counts.most_common()), "detected_now": len(found)}

    def summary(self, data: dict[str, Any]) -> str:
        total = sum(data["languages"].values()) or 1
        return ", ".join(f"{k} {v / total:.0%}" for k, v in list(data["languages"].items())[:6])

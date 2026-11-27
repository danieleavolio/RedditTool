"""Counts, rankings and activity over time (wraps ``collection_stats``)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.stats import collection_stats
from reddit_analyzer.storage import Database


class StatsAnalyzer(Analyzer):
    name = "stats"
    description = "Posts, comments, activity over time, top subreddits and authors."

    def run(self, db: Database, collection: str | None) -> dict[str, Any]:
        return asdict(collection_stats(db, collection))

    def summary(self, data: dict[str, Any]) -> str:
        if not data["posts"]:
            return "No posts."
        subs = ", ".join(f"r/{n} ({c})" for n, c in data["top_subreddits"][:3])
        return (
            f"{data['posts']} posts, {data['comments']} comments, "
            f"{data['first_post']} to {data['last_post']}, mean score {data['score_mean']:.1f}\n"
            f"top subreddits: {subs}"
        )

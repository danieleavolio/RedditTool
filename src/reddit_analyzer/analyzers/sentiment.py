"""Sentiment with VADER, which only understands English: other languages are not scored.

A wrong score is worse than none, so posts in other (or undetectable) languages are counted
as skipped instead of being forced through an English lexicon.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.datasets.filters import detect_language
from reddit_analyzer.storage import Database
from reddit_analyzer.text import post_text

POSITIVE, NEGATIVE = 0.05, -0.05  # the thresholds suggested by VADER's authors


def label(compound: float) -> str:
    if compound >= POSITIVE:
        return "positive"
    return "negative" if compound <= NEGATIVE else "neutral"


class SentimentAnalyzer(Analyzer):
    name = "sentiment"
    description = "Sentiment of English posts (VADER). Other languages are skipped."
    requires = ("vaderSentiment", "langdetect")
    extra = "nlp"

    def run(self, db: Database, collection: str | None) -> dict[str, Any]:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        vader = SentimentIntensityAnalyzer()
        labels: Counter[str] = Counter()
        by_month: defaultdict[str, list[float]] = defaultdict(list)
        scores: list[float] = []
        skipped = 0
        for post in db.iter_posts(collection=collection, oldest_first=True):
            text = post_text(post)
            if (post.lang or detect_language(text)) != "en":
                skipped += 1
                continue
            compound = vader.polarity_scores(text)["compound"]
            scores.append(compound)
            by_month[post.created_utc.strftime("%Y-%m")].append(compound)
            labels[label(compound)] += 1
        return {
            "analyzed": len(scores),
            "skipped_not_english": skipped,
            "mean": round(sum(scores) / len(scores), 4) if scores else None,
            "labels": {k: labels[k] for k in ("positive", "neutral", "negative")},
            "by_month": [(m, round(sum(v) / len(v), 4)) for m, v in sorted(by_month.items())],
        }

    def summary(self, data: dict[str, Any]) -> str:
        if not data["analyzed"]:
            return f"No English posts to score ({data['skipped_not_english']} skipped)."
        lab = data["labels"]
        return (
            f"{data['analyzed']} English posts, mean {data['mean']:+.2f} "
            f"({lab['positive']} positive, {lab['neutral']} neutral, {lab['negative']} negative); "
            f"{data['skipped_not_english']} skipped (other language)"
        )

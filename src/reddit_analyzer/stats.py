"""Basic statistics over a collection. Pure functions: the interfaces only display the result.

The ``stats`` analyzer (``reddit_analyzer.analyzers.stats``) stores this same result.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from reddit_analyzer.storage import Database
from reddit_analyzer.text import post_text
from reddit_analyzer.text import words as text_words


@dataclass(frozen=True)
class CollectionStats:
    posts: int = 0
    comments: int = 0
    first_post: str | None = None  # YYYY-MM of the oldest post
    last_post: str | None = None
    score_mean: float = 0.0
    top_subreddits: list[tuple[str, int]] = field(default_factory=list)
    top_authors: list[tuple[str, int]] = field(default_factory=list)
    posts_per_month: list[tuple[str, int]] = field(default_factory=list)  # chronological
    top_words: list[tuple[str, int]] = field(default_factory=list)
    activity: list[list[int]] = field(default_factory=list)  # [weekday Mon=0][hour], UTC


def collection_stats(db: Database, collection: str | None = None, top: int = 10) -> CollectionStats:
    """Counts and rankings for one collection (or the whole database when ``None``)."""
    subreddits: Counter[str] = Counter()
    authors: Counter[str] = Counter()
    months: Counter[str] = Counter()
    words: Counter[str] = Counter()
    total = score_sum = 0
    activity = [[0] * 24 for _ in range(7)]
    for post in db.iter_posts(collection=collection, oldest_first=True):
        total += 1
        score_sum += post.score
        activity[post.created_utc.weekday()][post.created_utc.hour] += 1
        subreddits[post.subreddit] += 1
        if post.author:
            authors[post.author] += 1
        months[post.created_utc.strftime("%Y-%m")] += 1
        words.update(text_words(post_text(post)))
    if not total:
        return CollectionStats(comments=db.count_comments(collection))
    ordered = sorted(months)
    return CollectionStats(
        posts=total,
        comments=db.count_comments(collection),
        first_post=ordered[0],
        last_post=ordered[-1],
        score_mean=score_sum / total,
        top_subreddits=subreddits.most_common(top),
        top_authors=authors.most_common(top),
        posts_per_month=[(m, months[m]) for m in ordered],
        top_words=words.most_common(top * 2),
        activity=activity,
    )

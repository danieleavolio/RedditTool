"""Basic statistics over a collection. Pure functions: the interfaces only display the result.

This is the seed of the analyzers of phase 8 (keywords by TF-IDF and sentiment come there).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from reddit_analyzer.storage import Database

_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_URL = re.compile(r"https?://\S+")
# Small multilingual list: enough to keep the top words readable, not a linguistic resource.
_STOPWORDS = frozenset(
    """that this with from have there their about would could which what when your will been
    were they them then than also just like into more some very only over such other because
    where while these those being does doing here again once each both cannot dont
    che non per una sono come anche più questo questa quello della delle degli dello nel nella
    nelle nei alla alle agli allo con del dei gli suo sua suoi sue loro dove quando perché
    perche cosa tutto tutti tutte molto ancora solo sulla sulle essere stato stata fatto
    hanno aveva ogni però pero oppure""".split()
)


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


def collection_stats(db: Database, collection: str | None = None, top: int = 10) -> CollectionStats:
    """Counts and rankings for one collection (or the whole database when ``None``)."""
    subreddits: Counter[str] = Counter()
    authors: Counter[str] = Counter()
    months: Counter[str] = Counter()
    words: Counter[str] = Counter()
    total = score_sum = 0
    for post in db.iter_posts(collection=collection, oldest_first=True):
        total += 1
        score_sum += post.score
        subreddits[post.subreddit] += 1
        if post.author:
            authors[post.author] += 1
        months[post.created_utc.strftime("%Y-%m")] += 1
        text = _URL.sub(" ", f"{post.title} {post.selftext}").lower()
        words.update(w for w in _WORD.findall(text) if w not in _STOPWORDS)
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
    )

"""Row filters. Each check returns the *reason* a row is dropped, or ``None`` to keep it,
so the build statistics can say why rows disappeared."""

from __future__ import annotations

from datetime import datetime

from reddit_analyzer.datasets.recipe import Filters
from reddit_analyzer.errors import DatasetError
from reddit_analyzer.models import Comment, ContentStatus, Post

_BOT_NAMES = frozenset({"automoderator"})
_MAX_DETECT_CHARS = 2000


def is_bot(author: str | None) -> bool:
    if not author:
        return False
    name = author.lower()
    return name in _BOT_NAMES or name.endswith("bot") or name.endswith("_bot")


def detect_language(text: str) -> str | None:
    """ISO code of the dominant language, or ``None`` when the text is too short to tell.

    Deterministic: ``langdetect`` is seeded, so the same text always gets the same answer.
    """
    try:
        from langdetect import DetectorFactory, detect
        from langdetect.lang_detect_exception import LangDetectException
    except ImportError as exc:
        raise DatasetError(
            "The 'lang' filter needs language detection. "
            "Install it with: pip install reddit-post-analyzer[nlp]"
        ) from exc
    DetectorFactory.seed = 0
    try:
        return detect(text[:_MAX_DETECT_CHARS]).lower()
    except LangDetectException:
        return None


class FilterSet:
    def __init__(self, filters: Filters):
        self.f = filters
        self._authors = frozenset(filters.exclude_authors)
        self._subreddits = frozenset(filters.subreddits)

    # -- checks on the post or comment itself -------------------------------------------

    def status_reason(self, author: str | None, status: ContentStatus) -> str | None:
        f = self.f
        if f.exclude_removed and status is not ContentStatus.OK:
            return "removed"
        if f.exclude_bots and is_bot(author):
            return "bot"
        if author and author.lower() in self._authors:
            return "author"
        return None

    def stats_reason(self, score: int, created: datetime) -> str | None:
        f = self.f
        if f.min_score is not None and score < f.min_score:
            return "score"
        if f.max_score is not None and score > f.max_score:
            return "score"
        if f.after is not None and created < f.after:
            return "date"
        if f.before is not None and created >= f.before:
            return "date"
        return None

    def meta_reason(self, post: Post) -> str | None:
        """Checks that always concern the post, even when the unit is a comment."""
        if self._subreddits and post.subreddit.lower() not in self._subreddits:
            return "subreddit"
        if self.f.nsfw == "exclude" and post.over_18:
            return "nsfw"
        if self.f.nsfw == "only" and not post.over_18:
            return "nsfw"
        return None

    def post_reason(self, post: Post) -> str | None:
        return (
            self.meta_reason(post)
            or self.status_reason(post.author, post.status)
            or self.stats_reason(post.score, post.created_utc)
        )

    def comment_reason(self, comment: Comment) -> str | None:
        return self.status_reason(comment.author, comment.status) or self.stats_reason(
            comment.score, comment.created_utc
        )

    # -- checks on the cleaned text -----------------------------------------------------

    def length_reason(self, text: str) -> str | None:
        f = self.f
        if f.min_chars is not None and len(text) < f.min_chars:
            return "short"
        if f.max_chars is not None and len(text) > f.max_chars:
            return "long"
        return None

    def lang_reason(self, text: str, known: str | None = None) -> str | None:
        """``known`` is a language already stored for the post; detection is the fallback."""
        if not self.f.lang:
            return None
        language = (known or detect_language(text) or "").lower()
        return None if language in self.f.lang else "lang"

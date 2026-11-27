"""The interface every data source implements, so storage and datasets stay source-agnostic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from reddit_analyzer.models import Comment, CommentsSpec, ListingParams, Post, SearchParams

# limit:     the requested number of posts was reached
# exhausted: the source has no more results for this query
# cap:       the source stopped at its own per-listing ceiling (Reddit: ~1000 items) before
#            the requested limit. Combine several sorts or time windows to go further.
EndReason = Literal["limit", "exhausted", "cap"]


@dataclass(frozen=True)
class PostPage:
    posts: list[Post]
    after: str | None  # cursor to resume from; saved by the runner after every page
    end_reason: EndReason | None  # None while more pages are available


class Source(ABC):
    name: str

    @abstractmethod
    def iter_pages(
        self, params: SearchParams | ListingParams, after: str | None = None, fetched: int = 0
    ) -> Iterator[PostPage]:
        """Yield pages of posts. ``after``/``fetched`` resume an interrupted run."""

    @abstractmethod
    def iter_comments(self, post_id: str, spec: CommentsSpec | None = None) -> Iterator[Comment]:
        """Yield the comments of one post, within the limits given by ``spec``."""

    @abstractmethod
    def refresh(self, ids: Sequence[str]) -> Iterator[Post]:
        """Fetch current state (score, removed/deleted) for already known post ids."""

    def iter_posts(self, params: SearchParams | ListingParams) -> Iterator[Post]:
        for page in self.iter_pages(params):
            yield from page.posts

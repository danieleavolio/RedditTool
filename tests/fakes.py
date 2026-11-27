"""An in-memory Source for storage and runner tests, plus a few model builders."""

from collections.abc import Iterator, Sequence

from payloads import post_data

from reddit_analyzer.errors import ServerError
from reddit_analyzer.models import Comment, CommentsSpec, ListingParams, Post, SearchParams
from reddit_analyzer.sources.base import PostPage, Source


def make_post(n: int, **overrides) -> Post:
    return Post.from_reddit(post_data(n, **overrides))


def make_comment(post_n: int, n: int, **overrides) -> Comment:
    data = {
        "id": f"c{post_n:04d}_{n}",
        "link_id": f"t3_p{post_n:04d}",
        "parent_id": f"t3_p{post_n:04d}",
        "depth": 0,
        "author": "replier",
        "body": f"Comment {n} on {post_n}",
        "score": n,
        "created_utc": 1767225600 + post_n * 100 + n,
    }
    data.update(overrides)
    return Comment.from_reddit(data)


class FakeSource(Source):
    """Serves ``total`` posts in pages, honouring ``after``/``fetched`` like Reddit does.

    ``fail_on_page_call`` makes the n-th page request (counted across the instance) raise.
    ``fail_comments_for`` makes fetching the comments of that post number raise.
    """

    name = "fake"

    def __init__(
        self,
        total: int = 25,
        page_size: int = 10,
        comments_per_post: int = 2,
        fail_on_page_call: int | None = None,
        fail_comments_for: int | None = None,
    ):
        self.total = total
        self.page_size = page_size
        self.comments_per_post = comments_per_post
        self.fail_on_page_call = fail_on_page_call
        self.fail_comments_for = fail_comments_for
        self.page_calls = 0

    def iter_pages(
        self, params: SearchParams | ListingParams, after: str | None = None, fetched: int = 0
    ) -> Iterator[PostPage]:
        start = int(after) if after else 0
        while True:
            self.page_calls += 1
            if self.fail_on_page_call == self.page_calls:
                raise ServerError("simulated outage")
            size = min(self.page_size, params.limit - fetched, self.total - start)
            posts = [make_post(i) for i in range(start, start + max(size, 0))]
            start += len(posts)
            fetched += len(posts)
            if fetched >= params.limit:
                reason = "limit"
            elif start >= self.total:
                reason = "exhausted"
            else:
                reason = None
            yield PostPage(posts, None if reason else str(start), reason)
            if reason:
                return

    def iter_comments(self, post_id: str, spec: CommentsSpec | None = None) -> Iterator[Comment]:
        n = int(post_id.removeprefix("p"))
        if self.fail_comments_for == n:
            raise ServerError("simulated outage while reading comments")
        for k in range(self.comments_per_post):
            yield make_comment(n, k)

    def refresh(self, ids: Sequence[str]) -> Iterator[Post]:
        yield from (make_post(int(i.removeprefix("p"))) for i in ids)

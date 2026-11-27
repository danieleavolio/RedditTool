"""Hits the real Reddit API. Run with: uv run pytest -m live

Needs RPA_CLIENT_ID, RPA_CLIENT_SECRET and RPA_REFRESH_TOKEN (e.g. from `rpa auth login`
output of your own approved app). Skipped when they are missing.
"""

import os

import pytest

from reddit_analyzer.models import CommentsSpec, SearchParams
from reddit_analyzer.sources.oauth import RedditClient

REQUIRED = ("RPA_CLIENT_ID", "RPA_CLIENT_SECRET", "RPA_REFRESH_TOKEN")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not all(os.environ.get(k) for k in REQUIRED), reason=f"needs {', '.join(REQUIRED)}"
    ),
]


def test_live_posts_and_comments():
    with RedditClient.from_config() as client:
        assert client.check_auth().username

        posts = list(
            client.iter_posts(SearchParams(query="python", subreddits=["python"], limit=50))
        )
        assert len(posts) == 50

        post = next(p for p in posts if p.num_comments > 0)
        comments = list(client.iter_comments(post.id, CommentsSpec(depth=2, max_per_post=20)))
        assert comments and all(c.post_id == post.id for c in comments)

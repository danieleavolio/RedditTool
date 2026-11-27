"""Builders for synthetic Reddit API responses used by the HTTP-mocked tests."""

import httpx


def post_data(n: int, **overrides) -> dict:
    data = {
        "id": f"p{n:04d}",
        "subreddit": "python",
        "author": "someone",
        "title": f"Post {n}",
        "selftext": "",
        "url": f"https://example.com/{n}",
        "permalink": f"/r/python/comments/p{n:04d}/post_{n}/",
        "score": n,
        "upvote_ratio": 0.9,
        "num_comments": 3,
        "created_utc": 1767225600 + n,
        "over_18": False,
        "is_self": False,
        "link_flair_text": None,
        "removed_by_category": None,
    }
    data.update(overrides)
    return data


def listing(posts: list[dict], after: str | None = None) -> dict:
    return {
        "kind": "Listing",
        "data": {"after": after, "children": [{"kind": "t3", "data": p} for p in posts]},
    }


def posts_page(start: int, count: int, after: str | None) -> dict:
    return listing([post_data(i) for i in range(start, start + count)], after)


def ratelimit_headers(remaining: int = 90, used: int = 10, reset: int = 30) -> dict:
    return {
        "x-ratelimit-remaining": str(remaining),
        "x-ratelimit-used": str(used),
        "x-ratelimit-reset": str(reset),
    }


def ok(payload: dict | list, **headers) -> httpx.Response:
    return httpx.Response(200, json=payload, headers={**ratelimit_headers(), **headers})

"""The columns a dataset row can have, per unit (post, comment or post -> top reply pair)."""

from __future__ import annotations

from typing import Literal

Unit = Literal["post", "comment", "pair"]

# Column name -> type ("str", "int", "float", "bool"). ``created_utc`` is an ISO 8601 string
# ("2026-01-31T09:30:00Z") so every format round-trips it identically.
UNIT_FIELDS: dict[str, dict[str, str]] = {
    "post": {
        "id": "str", "subreddit": "str", "author": "str", "created_utc": "str",
        "score": "int", "upvote_ratio": "float", "num_comments": "int", "title": "str",
        "selftext": "str", "url": "str", "permalink": "str", "flair": "str",
        "over_18": "bool", "is_self": "bool", "lang": "str", "text": "str",
    },
    "comment": {
        "id": "str", "post_id": "str", "subreddit": "str", "parent_id": "str", "depth": "int",
        "author": "str", "created_utc": "str", "score": "int", "title": "str", "body": "str",
        "text": "str",
    },
    "pair": {
        "id": "str", "subreddit": "str", "author": "str", "created_utc": "str", "score": "int",
        "num_comments": "int", "title": "str", "selftext": "str", "permalink": "str",
        "comment_id": "str", "comment_author": "str", "comment_score": "int", "body": "str",
        "text": "str", "response": "str",
    },
}  # fmt: skip

# What a recipe outputs when ``output.fields`` is not given.
DEFAULT_FIELDS: dict[str, list[str]] = {
    "post": ["id", "subreddit", "created_utc", "score", "num_comments", "text"],
    "comment": ["id", "post_id", "subreddit", "created_utc", "score", "text"],
    "pair": ["id", "subreddit", "created_utc", "score", "text", "response"],
}

DEFAULT_TEMPLATE: dict[str, str] = {
    "post": "{title}\n\n{selftext}",
    "comment": "{body}",
    "pair": "{title}\n\n{selftext}",
}

# Computed from the template and the cleaner, so a template cannot refer to them.
DERIVED = frozenset({"text", "response"})


def field_types(unit: str, fields: list[str]) -> dict[str, str]:
    return {f: UNIT_FIELDS[unit][f] for f in fields}

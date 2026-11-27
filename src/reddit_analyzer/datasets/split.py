"""Deterministic partitions, grouped by thread."""

from __future__ import annotations

import hashlib

from reddit_analyzer.datasets.recipe import Split


def bucket(post_id: str, seed: int) -> float:
    """A stable number in [0, 1) for this post and seed."""
    digest = hashlib.blake2b(f"{seed}:{post_id}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def assign_part(post_id: str, split: Split) -> str:
    """The part a post (and every comment of it) belongs to.

    Depends only on the post id and the seed, never on the database contents or the row
    order, so adding posts later does not move the existing ones.
    """
    point, edge = bucket(post_id, split.seed), 0.0
    last = ""
    for name, share in split.parts.items():
        edge += share
        last = name
        if point < edge:
            return name
    return last  # floating point slack at the very top of the range

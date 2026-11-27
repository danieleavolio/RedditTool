from datetime import UTC

import pytest
from pydantic import TypeAdapter, ValidationError

from reddit_analyzer.models import (
    Collection,
    Comment,
    ContentStatus,
    ListingParams,
    Post,
    Run,
    RunParams,
    RunStatus,
    SearchParams,
)


def _children(listing):
    return [c["data"] for c in listing["data"]["children"]]


def _walk_comments(children):
    """Flatten a comment tree, skipping `more` objects (the real walker lives in phase 2)."""
    for child in children:
        if child["kind"] != "t1":
            continue
        yield child["data"]
        replies = child["data"].get("replies")
        if replies:
            yield from _walk_comments(replies["data"]["children"])


def test_parse_search_listing(load_fixture):
    posts = [Post.from_reddit(d) for d in _children(load_fixture("listing_search.json"))]

    self_post, link_post, nsfw_post = posts
    assert self_post.id == "aaa111"
    assert self_post.fullname == "t3_aaa111"
    assert self_post.full_url == "https://www.reddit.com/r/italy/comments/aaa111/cosa_ne_pensate/"
    assert self_post.author == "mario_rossi"
    assert self_post.score == 154
    assert self_post.upvote_ratio == 0.93
    assert self_post.flair == "Discussione"
    assert self_post.is_self and not self_post.over_18
    assert self_post.status is ContentStatus.OK
    assert self_post.created_utc.tzinfo is UTC
    assert self_post.created_utc.isoformat() == "2026-01-01T00:00:00+00:00"

    assert not link_post.is_self
    assert link_post.selftext == ""
    assert link_post.flair is None

    assert nsfw_post.over_18
    assert nsfw_post.created_utc.microsecond == 500_000


def test_raw_keeps_original_json(load_fixture):
    data = _children(load_fixture("listing_search.json"))[0]
    post = Post.from_reddit(data)
    assert post.raw["domain"] == "self.italy"
    assert "raw" not in repr(post)


def test_removed_deleted_and_missing_fields(load_fixture):
    removed, deleted, minimal = (
        Post.from_reddit(d) for d in _children(load_fixture("edge_cases.json"))
    )
    assert removed.status is ContentStatus.REMOVED
    assert removed.author == "someone"

    assert deleted.status is ContentStatus.DELETED
    assert deleted.author is None
    assert deleted.upvote_ratio is None
    assert deleted.flair is None

    assert minimal.status is ContentStatus.OK
    assert minimal.selftext == ""
    assert minimal.score == 0
    assert minimal.num_comments == 0
    assert minimal.upvote_ratio is None
    assert not minimal.over_18


def test_parse_comment_thread(load_fixture):
    post_listing, comments_listing = load_fixture("comments_thread.json")
    post = Post.from_reddit(_children(post_listing)[0])
    comments = [
        Comment.from_reddit(d) for d in _walk_comments(comments_listing["data"]["children"])
    ]

    assert [c.id for c in comments] == ["c1", "c2", "c3", "c4"]
    assert all(c.post_id == post.id for c in comments)

    c1, c2, c3, c4 = comments
    assert c1.parent_id == "t3_aaa111" and c1.depth == 0
    assert c2.parent_id == "t1_c1" and c2.depth == 1
    assert c1.fullname == "t1_c1"

    assert c2.author is None and c2.status is ContentStatus.DELETED
    assert c3.author == "AutoModerator" and c3.status is ContentStatus.REMOVED
    assert c4.status is ContentStatus.OK


def test_models_are_frozen_and_strict(load_fixture):
    post = Post.from_reddit(_children(load_fixture("listing_search.json"))[0])
    with pytest.raises(ValidationError):
        post.score = 1
    with pytest.raises(ValidationError):
        Collection(name="ok", unknown_field=1)


def test_run_params_discriminated_union():
    adapter = TypeAdapter(RunParams)
    search = adapter.validate_python(
        {"kind": "search", "query": "rust", "subreddits": ["r/programming"]}
    )
    listing = adapter.validate_python(
        {"kind": "listing", "subreddit": "italy", "sort": "top", "time": "year"}
    )

    assert isinstance(search, SearchParams)
    assert search.subreddits == ["programming"]  # "r/" prefix stripped
    assert isinstance(listing, ListingParams)
    assert listing.sort == "top"


@pytest.mark.parametrize("bad", ["a", "has space", "way_too_long_subreddit_name", "x/y"])
def test_invalid_subreddit_rejected(bad):
    with pytest.raises(ValidationError):
        ListingParams(subreddit=bad)


def test_invalid_sort_and_limit_rejected():
    with pytest.raises(ValidationError):
        SearchParams(query="x", sort="rising")  # rising is a listing sort, not a search sort
    with pytest.raises(ValidationError):
        SearchParams(query="x", limit=0)


def test_run_defaults_and_update():
    run = Run(collection="rust", params=SearchParams(query="rust"))
    assert run.id is None
    assert run.status is RunStatus.PENDING
    assert run.source == "reddit-oauth"
    assert run.posts_fetched == 0
    assert run.created_at.tzinfo is UTC

    updated = run.model_copy(update={"status": RunStatus.RUNNING, "cursor": "t3_abc"})
    assert updated.cursor == "t3_abc" and run.cursor is None


def test_run_roundtrips_through_json():
    run = Run(collection="rust", params=ListingParams(subreddit="rust", limit=10))
    assert Run.model_validate_json(run.model_dump_json()) == run


@pytest.mark.parametrize("name", ["ai-italia-2026", "rust", "a_b"])
def test_collection_valid_names(name):
    assert Collection(name=name).name == name


@pytest.mark.parametrize("name", ["", "Has Upper", "-leading", "has space", "x" * 65])
def test_collection_invalid_names(name):
    with pytest.raises(ValidationError):
        Collection(name=name)

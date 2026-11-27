import copy
from itertools import count

import httpx
import pytest
from payloads import listing, ok, post_data, posts_page, ratelimit_headers

from reddit_analyzer.config import load_settings
from reddit_analyzer.errors import (
    AuthError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    RedditError,
    ServerError,
)
from reddit_analyzer.models import CommentsSpec, ListingParams, SearchParams
from reddit_analyzer.sources.oauth import BASE_URL


def _params(call) -> dict:
    return dict(call.request.url.params)


# -- auth / headers --------------------------------------------------------------------


def test_check_auth_reports_user_and_rate_limit(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        return_value=ok({"name": "bob"}, **ratelimit_headers(remaining=77, used=23, reset=12))
    )
    with make_client() as client:
        status = client.check_auth()
    assert (status.username, status.ratelimit_remaining, status.ratelimit_used) == ("bob", 77, 23)
    assert status.ratelimit_reset_seconds == 12
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer tok"
    assert request.headers["user-agent"].startswith("python:reddit-post-analyzer:")
    assert request.headers["user-agent"].endswith("(by /u/bob)")
    assert request.url.params["raw_json"] == "1"


def test_401_refreshes_token_once_then_succeeds(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        side_effect=[httpx.Response(401), ok({"name": "bob"})]
    )
    with make_client() as client:
        assert client.check_auth().username == "bob"
    assert mock_reddit.token.call_count == 2


def test_persistent_401_raises_auth_error(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(return_value=httpx.Response(401))
    with make_client() as client, pytest.raises(AuthError, match="rpa auth login"):
        client.check_auth()
    assert route.call_count == 2  # one retry after refreshing the token, then give up


# -- errors, retries, rate limiting ----------------------------------------------------


def test_429_waits_retry_after_then_succeeds(mock_reddit, make_client, sleeps):
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        side_effect=[httpx.Response(429, headers={"retry-after": "7"}), ok({"name": "bob"})]
    )
    with make_client() as client:
        client.check_auth()
    assert len(sleeps) == 1 and sleeps[0] >= 7


def test_persistent_429_raises_with_wait_time(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(429, headers={"x-ratelimit-reset": "42"})
    )
    max_retries = load_settings().collect.max_retries
    with make_client() as client, pytest.raises(RateLimitedError, match="42s") as info:
        client.check_auth()
    assert info.value.retry_after == 42
    assert route.call_count == max_retries + 1


def test_5xx_is_retried_with_backoff(mock_reddit, make_client, sleeps):
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        side_effect=[httpx.Response(503), httpx.Response(500), ok({"name": "bob"})]
    )
    with make_client() as client:
        assert client.check_auth().username == "bob"
    assert len(sleeps) == 2 and sleeps[1] > sleeps[0] * 0.9


def test_persistent_5xx_raises_server_error(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(return_value=httpx.Response(502))
    with make_client() as client, pytest.raises(ServerError):
        client.check_auth()


def test_network_errors_are_retried_then_raised(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        side_effect=[httpx.ConnectError("boom"), ok({"name": "bob"})]
    )
    with make_client() as client:
        assert client.check_auth().username == "bob"
    assert route.call_count == 2

    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(side_effect=httpx.ConnectError("boom"))
    with make_client() as client, pytest.raises(ServerError, match="Network error"):
        client.check_auth()


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(403, json={"reason": "private"}), ForbiddenError),
        (httpx.Response(404), NotFoundError),
        (httpx.Response(302, headers={"location": "/subreddits/search"}), NotFoundError),
        (httpx.Response(418), RedditError),
        (httpx.Response(200, text="<html>not json</html>"), RedditError),
    ],
)
def test_error_mapping(mock_reddit, make_client, response, error):
    mock_reddit.get(f"{BASE_URL}/r/nope/new").mock(return_value=response)
    with make_client() as client, pytest.raises(error):
        list(client.iter_pages(ListingParams(subreddit="nope", limit=10)))


def test_waits_for_reset_before_exhausting_quota(mock_reddit, make_client, sleeps):
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        return_value=ok({"name": "bob"}, **ratelimit_headers(remaining=2, reset=10))
    )
    with make_client() as client:
        client.check_auth()
        assert sleeps == []
        client.check_auth()  # remaining (2) is below the reserve (5): wait for the reset first
    assert sleeps == [11.0]


# -- posts ------------------------------------------------------------------------------


def test_search_paginates_and_respects_limit(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/search").mock(
        side_effect=[ok(posts_page(0, 100, "t3_p0099")), ok(posts_page(100, 50, "t3_p0149"))]
    )
    params = SearchParams(query="rust lang", sort="top", time="year", limit=150)
    with make_client() as client:
        pages = list(client.iter_pages(params))

    assert [len(p.posts) for p in pages] == [100, 50]
    assert [p.end_reason for p in pages] == [None, "limit"]
    assert pages[0].after == "t3_p0099"
    first, second = (_params(c) for c in route.calls)
    assert first == {
        "q": "rust lang",
        "sort": "top",
        "t": "year",
        "type": "link",
        "limit": "100",
        "raw_json": "1",
    }
    assert second["limit"] == "50" and second["after"] == "t3_p0099"


def test_search_in_subreddits_uses_multireddit_and_restrict_sr(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/r/italy+programming/search").mock(
        return_value=ok(posts_page(0, 3, None))
    )
    params = SearchParams(query="ai", subreddits=["italy", "programming"], limit=10)
    with make_client() as client:
        posts = list(client.iter_posts(params))
    assert len(posts) == 3
    assert _params(route.calls.last)["restrict_sr"] == "1"


@pytest.mark.parametrize(
    ("sort", "sends_t"), [("top", True), ("controversial", True), ("new", False)]
)
def test_listing_sends_time_filter_only_for_top_and_controversial(
    mock_reddit, make_client, sort, sends_t
):
    route = mock_reddit.get(f"{BASE_URL}/r/italy/{sort}").mock(
        return_value=ok(posts_page(0, 2, None))
    )
    with make_client() as client:
        list(client.iter_pages(ListingParams(subreddit="italy", sort=sort, time="week", limit=10)))
    assert ("t" in _params(route.calls.last)) is sends_t


def test_exhausted_and_empty_results(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/search").mock(return_value=ok(posts_page(0, 30, None)))
    with make_client() as client:
        (page,) = client.iter_pages(SearchParams(query="x", limit=100))
    assert (len(page.posts), page.end_reason) == (30, "exhausted")

    mock_reddit.get(f"{BASE_URL}/search").mock(return_value=ok(listing([])))
    with make_client() as client:
        (page,) = client.iter_pages(SearchParams(query="x", limit=100))
    assert (page.posts, page.end_reason) == ([], "exhausted")


def test_reddit_listing_cap_is_reported_not_silent(mock_reddit, make_client):
    pages_served = count()

    def serve(request):
        n = next(pages_served)
        return ok(posts_page(n * 100, 100, f"t3_{n}" if n < 9 else None))

    mock_reddit.get(f"{BASE_URL}/search").mock(side_effect=serve)
    with make_client() as client:
        pages = list(client.iter_pages(SearchParams(query="x", limit=5000)))
    assert sum(len(p.posts) for p in pages) == 1000
    assert pages[-1].end_reason == "cap"


def test_resume_continues_from_cursor(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/search").mock(return_value=ok(posts_page(100, 50, None)))
    params = SearchParams(query="x", limit=150)
    with make_client() as client:
        (page,) = client.iter_pages(params, after="t3_p0099", fetched=100)
        assert page.end_reason == "limit"
        request = _params(route.calls.last)
        assert request["after"] == "t3_p0099" and request["limit"] == "50"

        calls_before = route.call_count
        (done,) = client.iter_pages(params, after="t3_p0149", fetched=150)
        assert done.posts == [] and done.end_reason == "limit"
        assert route.call_count == calls_before  # nothing left to fetch: no request


def test_malformed_post_is_skipped_not_fatal(mock_reddit, make_client):
    broken = post_data(1)
    del broken["title"]
    mock_reddit.get(f"{BASE_URL}/search").mock(
        return_value=ok(listing([post_data(0), broken, post_data(2)]))
    )
    with make_client() as client:
        posts = list(client.iter_posts(SearchParams(query="x", limit=10)))
    assert [p.id for p in posts] == ["p0000", "p0002"]


def test_unexpected_listing_format(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/search").mock(return_value=ok({"unexpected": True}))
    with make_client() as client, pytest.raises(RedditError, match="format"):
        list(client.iter_posts(SearchParams(query="x", limit=10)))


def test_refresh_uses_batches_of_100(mock_reddit, make_client):
    route = mock_reddit.get(f"{BASE_URL}/api/info").mock(
        side_effect=[ok(posts_page(0, 100, None)), ok(posts_page(100, 50, None))]
    )
    ids = [f"p{n:04d}" for n in range(150)]
    with make_client() as client:
        posts = list(client.refresh(ids))
    assert len(posts) == 150 and route.call_count == 2
    first_ids = _params(route.calls[0])["id"].split(",")
    assert len(first_ids) == 100 and first_ids[0] == "t3_p0000"
    assert len(_params(route.calls[1])["id"].split(",")) == 50


def test_refresh_marks_removed_posts(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/api/info").mock(
        return_value=ok(
            listing([post_data(1, removed_by_category="moderator", selftext="[removed]")])
        )
    )
    with make_client() as client:
        (post,) = client.refresh(["p0001"])
    assert post.status == "removed"


# -- comments ---------------------------------------------------------------------------


def _more_response(load_fixture):
    c1 = load_fixture("comments_thread.json")[1]["data"]["children"][0]["data"]
    template = {k: v for k, v in c1.items() if k != "replies"}

    def thing(cid):
        return {
            "kind": "t1",
            "data": {
                **template,
                "id": cid,
                "parent_id": "t1_c1",
                "depth": 1,
                "body": f"body {cid}",
                "replies": "",
            },
        }

    return {"json": {"errors": [], "data": {"things": [thing("c9"), thing("c10")]}}}


def test_comments_expand_more_children(mock_reddit, make_client, load_fixture):
    thread = mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(
        return_value=ok(load_fixture("comments_thread.json"))
    )
    more = mock_reddit.get(f"{BASE_URL}/api/morechildren").mock(
        return_value=ok(_more_response(load_fixture))
    )
    with make_client() as client:
        comments = list(client.iter_comments("aaa111", CommentsSpec(depth=2, max_per_post=50)))

    assert [c.id for c in comments] == ["c1", "c2", "c3", "c4", "c9", "c10"]
    assert (
        _params(thread.calls.last)["depth"] == "2" and _params(thread.calls.last)["limit"] == "50"
    )
    assert _params(more.calls.last) == {
        "api_type": "json",
        "link_id": "t3_aaa111",
        "children": "c9,c10",
        "raw_json": "1",
    }


def test_comments_stop_at_max_per_post_without_expanding(mock_reddit, make_client, load_fixture):
    mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(
        return_value=ok(load_fixture("comments_thread.json"))
    )
    more = mock_reddit.get(f"{BASE_URL}/api/morechildren").mock(
        return_value=ok(_more_response(load_fixture))
    )
    with make_client() as client:
        comments = list(client.iter_comments("aaa111", CommentsSpec(depth=2, max_per_post=3)))
    assert [c.id for c in comments] == ["c1", "c2", "c3"]
    assert more.call_count == 0


def test_comments_depth_limit_skips_deeper_comments_and_more(
    mock_reddit, make_client, load_fixture
):
    mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(
        return_value=ok(load_fixture("comments_thread.json"))
    )
    more = mock_reddit.get(f"{BASE_URL}/api/morechildren").mock(
        return_value=ok(_more_response(load_fixture))
    )
    with make_client() as client:
        comments = list(client.iter_comments("aaa111", CommentsSpec(depth=1, max_per_post=50)))
    assert [c.id for c in comments] == ["c1", "c4"]  # only top-level
    assert more.call_count == 0


def test_morechildren_cap_zero_never_calls_the_endpoint(mock_reddit, make_client, load_fixture):
    mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(
        return_value=ok(load_fixture("comments_thread.json"))
    )
    more = mock_reddit.get(f"{BASE_URL}/api/morechildren")
    settings = load_settings()
    settings = settings.model_copy(
        update={"collect": settings.collect.model_copy(update={"morechildren_cap": 0})}
    )
    with make_client(settings) as client:
        comments = list(client.iter_comments("aaa111"))
    assert [c.id for c in comments] == ["c1", "c2", "c3", "c4"]
    assert more.call_count == 0


def test_comments_are_deduplicated(mock_reddit, make_client, load_fixture):
    payload = copy.deepcopy(_more_response(load_fixture))
    payload["json"]["data"]["things"].append(payload["json"]["data"]["things"][0])  # c9 twice
    mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(
        return_value=ok(load_fixture("comments_thread.json"))
    )
    mock_reddit.get(f"{BASE_URL}/api/morechildren").mock(return_value=ok(payload))
    with make_client() as client:
        ids = [c.id for c in client.iter_comments("aaa111")]
    assert ids.count("c9") == 1


def test_comments_unexpected_format(mock_reddit, make_client):
    mock_reddit.get(f"{BASE_URL}/comments/aaa111").mock(return_value=ok({"nope": 1}))
    with make_client() as client, pytest.raises(RedditError, match="format"):
        list(client.iter_comments("aaa111"))

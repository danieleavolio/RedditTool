"""Reddit API client on https://oauth.reddit.com (OAuth only, no anonymous access)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import httpx
from pydantic import ValidationError

from reddit_analyzer.collect.ratelimit import RateLimiter
from reddit_analyzer.config import (
    CREDENTIALS_DOC,
    Credentials,
    Settings,
    build_user_agent,
    get_credentials,
    load_settings,
)
from reddit_analyzer.errors import (
    AuthError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    RedditError,
    ServerError,
)
from reddit_analyzer.models import (
    Comment,
    CommentsSpec,
    ListingParams,
    Model,
    Post,
    SearchParams,
)
from reddit_analyzer.sources.auth import TokenManager
from reddit_analyzer.sources.base import PostPage, Source

log = logging.getLogger(__name__)

BASE_URL = "https://oauth.reddit.com"
PAGE_SIZE = 100  # Reddit's maximum page size
LISTING_CAP = 1000  # Reddit stops paginating a listing after roughly this many items
MORECHILDREN_BATCH = 100


class AuthStatus(Model):
    username: str
    ratelimit_used: float | None
    ratelimit_remaining: float | None
    ratelimit_reset_seconds: float | None


def _retry_after(resp: httpx.Response) -> float | None:
    for header in ("retry-after", "x-ratelimit-reset"):
        try:
            return float(resp.headers[header])
        except (KeyError, ValueError):
            continue
    return None


def _error_for(resp: httpx.Response) -> RedditError:
    status = resp.status_code
    if status == 401:
        return AuthError(
            "Reddit rejected the access token (HTTP 401). Run `rpa auth login`. "
            f"See {CREDENTIALS_DOC}."
        )
    if status == 403:
        return ForbiddenError(
            "Access denied (HTTP 403): the app is not approved or was revoked, or the subreddit "
            "is private or quarantined."
        )
    if status == 404 or 300 <= status < 400:  # Reddit redirects unknown subreddits to a search
        return NotFoundError("Not found (HTTP 404): check the subreddit or post id.")
    return RedditError(f"Unexpected response from Reddit (HTTP {status}).")


def _children(listing: Any) -> list[dict[str, Any]]:
    try:
        return listing["data"]["children"]
    except (KeyError, TypeError) as exc:
        raise RedditError("Unexpected response format from Reddit.") from exc


class RedditClient(Source):
    name = "reddit-oauth"

    def __init__(
        self,
        credentials: Credentials,
        settings: Settings | None = None,
        *,
        http: httpx.Client | None = None,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._settings = settings or load_settings()
        self._cfg = self._settings.collect
        self._owns_http = http is None
        self._http = http or httpx.Client(timeout=self._cfg.timeout_seconds)
        self._user_agent = build_user_agent(credentials.username)
        self._tokens = TokenManager(self._http, credentials)
        self._limiter = limiter or RateLimiter(reserve=self._cfg.ratelimit_reserve, sleep=sleep)

    @classmethod
    def from_config(cls, settings: Settings | None = None) -> RedditClient:
        settings = settings or load_settings()
        return cls(get_credentials(settings), settings)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> RedditClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- HTTP ---------------------------------------------------------------------------

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET ``path`` and return decoded JSON, handling 401, 429, 5xx and network errors."""
        query = {**(params or {}), "raw_json": 1}  # raw_json=1: no HTML-escaped text
        attempt = 0
        refreshed = False
        while True:
            self._limiter.before_request()
            headers = {
                "Authorization": f"Bearer {self._tokens.get_token()}",
                "User-Agent": self._user_agent,
            }
            try:
                resp = self._http.get(f"{BASE_URL}{path}", params=query, headers=headers)
            except httpx.TransportError as exc:
                if attempt >= self._cfg.max_retries:
                    raise ServerError(f"Network error talking to Reddit: {exc}") from exc
                self._limiter.wait_backoff(attempt)
                attempt += 1
                continue

            self._limiter.update(resp.headers)
            status = resp.status_code
            if status == 401 and not refreshed:
                self._tokens.invalidate()  # token may have expired early: refresh once and retry
                refreshed = True
                continue
            if status == 429 or status >= 500:
                wait = _retry_after(resp)
                if attempt >= self._cfg.max_retries:
                    if status == 429:
                        hint = f" Retry in about {wait:.0f}s." if wait else ""
                        raise RateLimitedError(
                            f"Reddit rate limit exhausted (HTTP 429).{hint}", retry_after=wait
                        )
                    raise ServerError(f"Reddit server error (HTTP {status}). Try again later.")
                self._limiter.wait_backoff(attempt, wait)
                attempt += 1
                continue
            if status >= 300:
                raise _error_for(resp)
            try:
                return resp.json()
            except ValueError as exc:
                raise RedditError("Reddit returned a response that is not valid JSON.") from exc

    # -- Auth ---------------------------------------------------------------------------

    def check_auth(self) -> AuthStatus:
        """Call GET /api/v1/me: proves the credentials work and reports the rate limit."""
        me = self._request("/api/v1/me")
        try:
            username = me["name"]
        except (KeyError, TypeError) as exc:
            raise RedditError("Unexpected response from /api/v1/me.") from exc
        lim = self._limiter
        return AuthStatus(
            username=username,
            ratelimit_used=lim.used,
            ratelimit_remaining=lim.remaining,
            ratelimit_reset_seconds=lim.reset,
        )

    # -- Posts --------------------------------------------------------------------------

    @staticmethod
    def _listing_request(params: SearchParams | ListingParams) -> tuple[str, dict[str, Any]]:
        if isinstance(params, SearchParams):
            query: dict[str, Any] = {
                "q": params.query,
                "sort": params.sort,
                "t": params.time,
                "type": "link",
            }
            if params.subreddits:
                query["restrict_sr"] = 1
                return f"/r/{'+'.join(params.subreddits)}/search", query
            return "/search", query
        query = {"t": params.time} if params.sort in ("top", "controversial") else {}
        return f"/r/{params.subreddit}/{params.sort}", query

    @staticmethod
    def _parse_posts(listing: Any) -> list[Post]:
        posts = []
        for child in _children(listing):
            if child.get("kind") != "t3":
                continue
            try:
                posts.append(Post.from_reddit(child["data"]))
            except (KeyError, TypeError, ValidationError) as exc:
                # One malformed item must not kill a long run.
                log.warning("Skipping malformed post: %s", exc)
        return posts

    def iter_pages(
        self, params: SearchParams | ListingParams, after: str | None = None, fetched: int = 0
    ) -> Iterator[PostPage]:
        path, query = self._listing_request(params)
        if fetched >= params.limit:  # resumed run that already has everything
            yield PostPage(posts=[], after=after, end_reason="limit")
            return
        while True:
            size = min(PAGE_SIZE, params.limit - fetched)
            request = {**query, "limit": size}
            if after:
                request["after"] = after
            data = self._request(path, request)
            posts = self._parse_posts(data)
            fetched += len(posts)
            after = data["data"].get("after")
            if fetched >= params.limit:
                reason = "limit"
            elif not after:
                reason = "cap" if fetched >= LISTING_CAP * 0.9 else "exhausted"
            else:
                reason = None
            yield PostPage(posts=posts, after=after, end_reason=reason)
            if reason:
                return

    def refresh(self, ids: Sequence[str]) -> Iterator[Post]:
        ids = list(ids)
        for i in range(0, len(ids), PAGE_SIZE):
            fullnames = ",".join(f"t3_{post_id}" for post_id in ids[i : i + PAGE_SIZE])
            yield from self._parse_posts(self._request("/api/info", {"id": fullnames}))

    # -- Comments -----------------------------------------------------------------------

    @staticmethod
    def _walk(
        things: list[dict[str, Any]], max_depth: int, comments: list[Comment], more: list[str]
    ) -> None:
        """Collect comments (within ``max_depth``) and the ids hidden behind "more" objects."""
        for thing in things:
            kind, data = thing.get("kind"), thing.get("data", {})
            if kind == "t1":
                try:
                    comment = Comment.from_reddit(data)
                except (KeyError, TypeError, ValidationError) as exc:
                    log.warning("Skipping malformed comment: %s", exc)
                    continue
                if comment.depth < max_depth:
                    comments.append(comment)
                replies = data.get("replies")
                if replies:  # "" when there are none
                    RedditClient._walk(_children(replies), max_depth, comments, more)
            elif kind == "more" and data.get("depth", 0) < max_depth:
                more.extend(
                    data.get("children", [])
                )  # empty = "continue this thread" link: skipped

    def iter_comments(self, post_id: str, spec: CommentsSpec | None = None) -> Iterator[Comment]:
        spec = spec or CommentsSpec(
            depth=self._cfg.comments_depth, max_per_post=self._cfg.comments_max_per_post
        )
        payload = self._request(
            f"/comments/{post_id}", {"depth": spec.depth, "limit": spec.max_per_post}
        )
        try:
            top_level = _children(payload[1])
        except (IndexError, KeyError, TypeError) as exc:
            raise RedditError("Unexpected response format from Reddit.") from exc

        comments: list[Comment] = []
        more: list[str] = []
        self._walk(top_level, spec.depth, comments, more)

        seen: set[str] = set()
        yielded = 0
        calls = 0
        while True:
            for comment in comments:
                if comment.id in seen:
                    continue
                seen.add(comment.id)
                yield comment
                yielded += 1
                if yielded >= spec.max_per_post:
                    return
            if not more or calls >= self._cfg.morechildren_cap:
                return
            batch, more = more[:MORECHILDREN_BATCH], more[MORECHILDREN_BATCH:]
            data = self._request(
                "/api/morechildren",
                {"api_type": "json", "link_id": f"t3_{post_id}", "children": ",".join(batch)},
            )
            calls += 1
            try:
                things = data["json"]["data"]["things"]
            except (KeyError, TypeError) as exc:
                raise RedditError("Unexpected response from /api/morechildren.") from exc
            comments = []
            self._walk(things, spec.depth, comments, more)

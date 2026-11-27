"""Domain models shared by every part of the suite.

Conventions: models are immutable, unknown fields are rejected, missing values are
``None`` (never placeholder strings), timestamps are timezone-aware UTC datetimes and
ids are Reddit base36 ids without the ``t3_``/``t1_`` prefix. The Reddit JSON format is
only ever seen by the ``from_reddit`` constructors.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sort = Literal["relevance", "hot", "top", "new", "comments"]
ListingSort = Literal["hot", "new", "top", "rising", "controversial"]
TimeFilter = Literal["hour", "day", "week", "month", "year", "all"]

_SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_]{2,21}$")


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContentStatus(StrEnum):
    OK = "ok"
    REMOVED = "removed"  # removed by moderators / Reddit
    DELETED = "deleted"  # deleted by the author


def _utc(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=UTC)


def _author(name: str | None) -> str | None:
    return None if name in (None, "", "[deleted]") else name


def _body_status(text: str | None, removed_by_category: str | None = None) -> ContentStatus:
    if removed_by_category == "deleted" or text == "[deleted]":
        return ContentStatus.DELETED
    if removed_by_category or text == "[removed]":
        return ContentStatus.REMOVED
    return ContentStatus.OK


def _strip_prefix(fullname: str) -> str:
    return fullname.split("_", 1)[1] if "_" in fullname else fullname


class Post(Model):
    id: str
    subreddit: str
    author: str | None
    title: str
    selftext: str
    url: str
    permalink: str  # relative, e.g. "/r/python/comments/abc123/title/"
    score: int
    upvote_ratio: float | None
    num_comments: int
    created_utc: datetime
    over_18: bool
    is_self: bool
    flair: str | None
    status: ContentStatus
    lang: str | None = None  # filled by the language analyzer, never by a source
    raw: dict[str, Any] = Field(repr=False)

    @property
    def fullname(self) -> str:
        return f"t3_{self.id}"

    @property
    def full_url(self) -> str:
        return f"https://www.reddit.com{self.permalink}"

    @classmethod
    def from_reddit(cls, data: dict[str, Any]) -> Post:
        """Build a Post from the ``data`` object of a Reddit ``t3`` thing."""
        selftext = data.get("selftext") or ""
        return cls(
            id=data["id"],
            subreddit=data["subreddit"],
            author=_author(data.get("author")),
            title=data["title"],
            selftext=selftext,
            url=data["url"],
            permalink=data["permalink"],
            score=data.get("score", 0),
            upvote_ratio=data.get("upvote_ratio"),
            num_comments=data.get("num_comments", 0),
            created_utc=_utc(data["created_utc"]),
            over_18=bool(data.get("over_18", False)),
            is_self=bool(data.get("is_self", False)),
            flair=data.get("link_flair_text") or None,
            status=_body_status(selftext, data.get("removed_by_category")),
            raw=data,
        )


class Comment(Model):
    id: str
    post_id: str
    parent_id: str  # fullname: t3_... for top-level comments, t1_... for replies
    depth: int
    author: str | None
    body: str
    score: int
    created_utc: datetime
    status: ContentStatus
    raw: dict[str, Any] = Field(repr=False)

    @property
    def fullname(self) -> str:
        return f"t1_{self.id}"

    @classmethod
    def from_reddit(cls, data: dict[str, Any]) -> Comment:
        """Build a Comment from the ``data`` object of a Reddit ``t1`` thing."""
        body = data.get("body") or ""
        return cls(
            id=data["id"],
            post_id=_strip_prefix(data["link_id"]),
            parent_id=data["parent_id"],
            depth=data.get("depth", 0),
            author=_author(data.get("author")),
            body=body,
            score=data.get("score", 0),
            created_utc=_utc(data["created_utc"]),
            status=_body_status(body),
            raw=data,
        )


def _clean_subreddit(name: str) -> str:
    name = name.strip().removeprefix("/").removeprefix("r/")
    if not _SUBREDDIT_RE.match(name):
        raise ValueError(f"invalid subreddit name: {name!r}")
    return name


class CommentsSpec(Model):
    depth: int = Field(2, ge=1)
    max_per_post: int = Field(50, ge=1)


class SearchParams(Model):
    kind: Literal["search"] = "search"
    query: str = Field(min_length=1)
    subreddits: list[str] = Field(default_factory=list)  # empty = all of Reddit
    sort: Sort = "relevance"
    time: TimeFilter = "all"
    limit: int = Field(100, ge=1)
    comments: CommentsSpec | None = None

    @field_validator("subreddits")
    @classmethod
    def _subreddits(cls, value: list[str]) -> list[str]:
        return [_clean_subreddit(v) for v in value]


class ListingParams(Model):
    kind: Literal["listing"] = "listing"
    subreddit: str
    sort: ListingSort = "new"
    time: TimeFilter = "all"
    limit: int = Field(100, ge=1)
    comments: CommentsSpec | None = None

    @field_validator("subreddit")
    @classmethod
    def _subreddit(cls, value: str) -> str:
        return _clean_subreddit(value)


RunParams = Annotated[SearchParams | ListingParams, Field(discriminator="kind")]


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _now() -> datetime:
    return datetime.now(UTC)


class Run(Model):
    """One execution of a collection job. Updated via ``model_copy(update=...)``."""

    id: int | None = None  # assigned by the database
    collection: str
    source: str = "reddit-oauth"
    params: RunParams
    status: RunStatus = RunStatus.PENDING
    cursor: str | None = None  # Reddit ``after`` token, saved every page for resume
    posts_fetched: int = 0
    posts_inserted: int = 0
    posts_updated: int = 0
    comments_fetched: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Collection(Model):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    description: str = ""
    created_at: datetime = Field(default_factory=_now)

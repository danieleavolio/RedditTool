"""Errors raised while talking to Reddit. Messages are written for end users."""

from __future__ import annotations


class RedditError(Exception):
    """Base class for every error the suite raises on purpose."""


class AuthError(RedditError):
    """Bad, expired or missing credentials (HTTP 401, invalid refresh token...)."""


class ForbiddenError(RedditError):
    """HTTP 403: app not approved or revoked, or the subreddit is private/quarantined."""


class NotFoundError(RedditError):
    """HTTP 404: the subreddit or post does not exist (or is banned)."""


class RateLimitedError(RedditError):
    """HTTP 429 that persisted after the allowed retries."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(RedditError):
    """HTTP 5xx or network failure that persisted after the allowed retries."""


class CredentialStoreError(RedditError):
    """The system keyring is not available for writing."""


class StorageError(RedditError):
    """The local database is unusable, too new for this version, or a record is missing."""

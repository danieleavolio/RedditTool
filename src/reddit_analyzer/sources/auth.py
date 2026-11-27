"""Reddit OAuth2: authorization code flow with a local redirect, then refresh tokens.

The ``password`` grant is deliberately not supported (it needs a "script" app, which can no
longer be created, and does not work with 2FA). Secrets are never logged.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from reddit_analyzer.config import CREDENTIALS_DOC, Credentials
from reddit_analyzer.errors import AuthError, ServerError

AUTHORIZE_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REVOKE_URL = "https://www.reddit.com/api/v1/revoke_token"
SCOPES = ("read", "identity")  # minimal: read listings/comments, and /api/v1/me
EXPIRY_MARGIN = 60  # refresh this many seconds before the token expires

_LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": redirect_uri,
            "duration": "permanent",  # needed to receive a refresh token
            "scope": " ".join(SCOPES),
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def wait_for_code(redirect_uri: str, state: str, timeout: float = 180.0) -> str:
    """Listen on the local redirect URI until Reddit sends the user back with a code."""
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in _LOCAL_HOSTS or not parsed.port:
        raise AuthError(
            f"Redirect URI must look like http://localhost:8080 (got {redirect_uri!r}). "
            f"See {CREDENTIALS_DOC}."
        )
    result: dict[str, list[str]] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            if "code" not in query and "error" not in query:
                self.send_response(404)  # e.g. favicon requests
                self.end_headers()
                return
            result.update(query)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Authorization received. You can close this tab.")

        def log_message(self, *args: object) -> None:
            pass

    try:
        server = HTTPServer(("127.0.0.1", parsed.port), Handler)
    except OSError as exc:
        raise AuthError(
            f"Cannot listen on port {parsed.port} for the Reddit redirect: {exc}"
        ) from exc
    server.timeout = 0.5
    deadline = time.monotonic() + timeout
    try:
        while not result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if not result:
        raise AuthError("Timed out waiting for the Reddit authorization.")
    if "error" in result:
        raise AuthError(f"Reddit did not grant access: {result['error'][0]}.")
    if not secrets.compare_digest(result.get("state", [""])[0], state):
        raise AuthError("Authorization response had an unexpected state; aborting for safety.")
    return result["code"][0]


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    expires_in: int
    refresh_token: str | None
    scope: str


def _token_request(http: httpx.Client, client_id: str, client_secret: str, data: dict) -> dict:
    resp = http.post(TOKEN_URL, data=data, auth=(client_id, client_secret))
    if resp.status_code >= 500:
        raise ServerError(
            f"Reddit token endpoint failed (HTTP {resp.status_code}). Try again later."
        )
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if resp.status_code != 200 or "access_token" not in payload:
        reason = payload.get("error", f"HTTP {resp.status_code}")
        raise AuthError(
            f"Reddit rejected the credentials ({reason}). Run `rpa auth login` again, or check "
            f"that the app is still approved. See {CREDENTIALS_DOC}."
        )
    return payload


def exchange_code(
    http: httpx.Client, client_id: str, client_secret: str, code: str, redirect_uri: str
) -> TokenSet:
    payload = _token_request(
        http,
        client_id,
        client_secret,
        {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
    )
    if not payload.get("refresh_token"):
        raise AuthError(
            "Reddit did not return a refresh token; the authorization was not permanent."
        )
    return TokenSet(
        access_token=payload["access_token"],
        expires_in=int(payload.get("expires_in", 3600)),
        refresh_token=payload["refresh_token"],
        scope=payload.get("scope", ""),
    )


def revoke_token(http: httpx.Client, client_id: str, client_secret: str, token: str) -> None:
    """Best effort: ask Reddit to invalidate a refresh token."""
    http.post(
        REVOKE_URL,
        data={"token": token, "token_type_hint": "refresh_token"},
        auth=(client_id, client_secret),
    )


class TokenManager:
    """Hands out a valid access token, refreshing it before expiry and on demand (401)."""

    def __init__(
        self,
        http: httpx.Client,
        credentials: Credentials,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._http = http
        self._credentials = credentials
        self._clock = clock
        self._token: str | None = None
        self._expires_at = 0.0

    def get_token(self) -> str:
        if self._token is None or self._clock() >= self._expires_at - EXPIRY_MARGIN:
            self._refresh()
        assert self._token is not None
        return self._token

    def invalidate(self) -> None:
        self._token = None

    def _refresh(self) -> None:
        creds = self._credentials
        if creds.refresh_token is None:
            raise AuthError(f"Not logged in. Run `rpa auth login`. See {CREDENTIALS_DOC}.")
        payload = _token_request(
            self._http,
            creds.client_id,
            creds.client_secret.get_secret_value(),
            {
                "grant_type": "refresh_token",
                "refresh_token": creds.refresh_token.get_secret_value(),
            },
        )
        self._token = payload["access_token"]
        self._expires_at = self._clock() + int(payload.get("expires_in", 3600))

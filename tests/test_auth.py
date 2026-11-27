import socket
import threading
import urllib.request
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import SecretStr

from reddit_analyzer.config import Credentials
from reddit_analyzer.errors import AuthError, ServerError
from reddit_analyzer.sources.auth import (
    TokenManager,
    build_authorize_url,
    exchange_code,
    wait_for_code,
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_authorize_url():
    url = build_authorize_url("cid", "http://localhost:8080", "st4te")
    parsed = urlparse(url)
    q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert parsed.netloc == "www.reddit.com" and parsed.path == "/api/v1/authorize"
    assert q == {
        "client_id": "cid",
        "response_type": "code",
        "state": "st4te",
        "redirect_uri": "http://localhost:8080",
        "duration": "permanent",
        "scope": "read identity",
    }


def _hit(port: int, query: str) -> None:
    def go():
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/?{query}", timeout=5).read()
        except Exception:
            pass

    threading.Thread(target=go).start()


def test_wait_for_code_success():
    port = _free_port()
    _hit(port, "code=abc123&state=xyz")
    assert wait_for_code(f"http://localhost:{port}", "xyz", timeout=5) == "abc123"


def test_wait_for_code_state_mismatch():
    port = _free_port()
    _hit(port, "code=abc123&state=evil")
    with pytest.raises(AuthError, match="state"):
        wait_for_code(f"http://localhost:{port}", "xyz", timeout=5)


def test_wait_for_code_access_denied():
    port = _free_port()
    _hit(port, "error=access_denied&state=xyz")
    with pytest.raises(AuthError, match="access_denied"):
        wait_for_code(f"http://localhost:{port}", "xyz", timeout=5)


def test_wait_for_code_timeout():
    with pytest.raises(AuthError, match="Timed out"):
        wait_for_code(f"http://localhost:{_free_port()}", "xyz", timeout=0.6)


@pytest.mark.parametrize(
    "uri", ["https://localhost:8080", "http://example.com:8080", "http://localhost"]
)
def test_redirect_uri_must_be_local_http_with_port(uri):
    with pytest.raises(AuthError, match="Redirect URI"):
        wait_for_code(uri, "xyz", timeout=0.1)


def test_exchange_code_sends_basic_auth_and_grant(mock_reddit):
    mock_reddit.token.mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "A", "refresh_token": "R", "expires_in": 3600, "scope": "read"},
        )
    )
    with httpx.Client() as http:
        tokens = exchange_code(http, "cid", "sec", "CODE", "http://localhost:8080")
    assert (tokens.access_token, tokens.refresh_token) == ("A", "R")
    request = mock_reddit.token.calls.last.request
    assert request.headers["authorization"].startswith("Basic ")
    body = parse_qs(request.content.decode())
    assert body == {
        "grant_type": ["authorization_code"],
        "code": ["CODE"],
        "redirect_uri": ["http://localhost:8080"],
    }


def test_exchange_code_without_refresh_token_fails(mock_reddit):
    mock_reddit.token.mock(return_value=httpx.Response(200, json={"access_token": "A"}))
    with httpx.Client() as http, pytest.raises(AuthError, match="refresh token"):
        exchange_code(http, "cid", "sec", "CODE", "http://localhost:8080")


def test_exchange_code_rejected(mock_reddit):
    mock_reddit.token.mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    with httpx.Client() as http, pytest.raises(AuthError, match="invalid_grant"):
        exchange_code(http, "cid", "sec", "CODE", "http://localhost:8080")


def test_token_endpoint_server_error(mock_reddit):
    mock_reddit.token.mock(return_value=httpx.Response(503))
    with httpx.Client() as http, pytest.raises(ServerError):
        exchange_code(http, "cid", "sec", "CODE", "http://localhost:8080")


def test_token_manager_caches_and_refreshes_before_expiry(mock_reddit, creds):
    now = [0.0]
    with httpx.Client() as http:
        manager = TokenManager(http, creds, clock=lambda: now[0])
        assert manager.get_token() == "tok"
        now[0] = 3000  # still valid (3600 - 60 margin)
        manager.get_token()
        assert mock_reddit.token.call_count == 1
        now[0] = 3541  # inside the 60s margin
        manager.get_token()
        assert mock_reddit.token.call_count == 2
    body = parse_qs(mock_reddit.token.calls.last.request.content.decode())
    assert body == {"grant_type": ["refresh_token"], "refresh_token": ["rt"]}


def test_token_manager_invalidate_forces_refresh(mock_reddit, creds):
    with httpx.Client() as http:
        manager = TokenManager(http, creds)
        manager.get_token()
        manager.invalidate()
        manager.get_token()
    assert mock_reddit.token.call_count == 2


def test_revoked_refresh_token_points_to_login(mock_reddit, creds):
    mock_reddit.token.mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    with httpx.Client() as http, pytest.raises(AuthError, match="rpa auth login"):
        TokenManager(http, creds).get_token()


def test_missing_refresh_token_points_to_login():
    creds = Credentials(client_id="cid", client_secret=SecretStr("sec"))
    with httpx.Client() as http, pytest.raises(AuthError, match="rpa auth login"):
        TokenManager(http, creds).get_token()
